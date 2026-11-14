from django.core.management.base import BaseCommand
from django.db import transaction
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from Counter.models import Report, TotalCountReport
from Counter.main import count_words, sincronizar_palabras_total_count
from Counter.utils import (
    extraer_texto_pdf_inteligente,
    calcular_metricas_complejidad,
    contar_palabras_tecnicas,
)
from Counter.cleaner import limpiar_texto_estructural


def _init_worker():
    import os
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ComplexIndex.settings")
    django.setup()


def _worker_extract_and_metrics(item):
    """
    Función de trabajo aislada para ProcessPoolExecutor.
    Ejecuta el cómputo intensivo de CPU (PyMuPDF, OCR y análisis lingüístico) en memoria RAM
    sin interactuar con la base de datos para evitar bloqueos concurrentes.
    """
    report_id, file_path, extracted_text_prev, from_file = item
    try:
        if from_file and file_path and os.path.exists(file_path):
            texto = extraer_texto_pdf_inteligente(file_path)
        else:
            texto = extracted_text_prev or ""

        if not texto or not texto.strip():
            return (report_id, "", {}, {}, None)

        texto_limpio = limpiar_texto_estructural(texto)
        metricas = calcular_metricas_complejidad(texto_limpio)
        conteo = count_words(texto_limpio)
        return (report_id, texto_limpio, metricas, conteo, None)
    except Exception as e:
        return (report_id, "", {}, {}, str(e))


class Command(BaseCommand):
    help = (
        "Reprocesa los reportes existentes aplicando el nuevo motor lingüístico, "
        "recalculando métricas de legibilidad INFLESZ, complejidad y sincronizando palabras."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--workspace-id",
            type=int,
            default=None,
            help="ID del espacio de trabajo a reprocesar (por defecto todos).",
        )
        parser.add_argument(
            "--from-file",
            action="store_true",
            help="Vuelve a leer el archivo PDF físico en disco en lugar de usar el extracted_text guardado.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Límite máximo de reportes a reprocesar.",
        )
        parser.add_argument(
            "--only-residual",
            action="store_true",
            help="Filtra solo reportes con texto residual (entre 1 y 19 palabras).",
        )
        parser.add_argument(
            "--only-pending",
            action="store_true",
            help="Filtra solo reportes pendientes sin palabras (total_words NULL).",
        )
        parser.add_argument(
            "--report-ids",
            type=str,
            default=None,
            help="Lista de IDs de reportes separados por comas (ej. --report-ids 21,223,770).",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=1,
            help="Número de procesos en paralelo para extracción y OCR (ej. --workers 6).",
        )

    def handle(self, *args, **options):
        ws_id = options["workspace_id"]
        from_file = options["from_file"]
        limit = options["limit"]
        only_residual = options.get("only_residual", False)
        only_pending = options.get("only_pending", False)
        report_ids_str = options.get("report_ids")
        workers = max(1, options.get("workers", 1))

        self.stdout.write(self.style.MIGRATE_HEADING("=== REPROCESAMIENTO LINGÜÍSTICO DE REPORTES ==="))

        qs = Report.objects.all().select_related("workspace", "company")
        if ws_id:
            qs = qs.filter(workspace_id=ws_id)

        if report_ids_str:
            ids = [int(i.strip()) for i in report_ids_str.split(",") if i.strip().isdigit()]
            qs = qs.filter(id__in=ids)
            from_file = True
        elif only_residual:
            qs = qs.filter(total_words__gt=0, total_words__lt=20)
            from_file = True
        elif only_pending:
            qs = qs.filter(total_words__isnull=True)
            from_file = True
        elif not from_file:
            # Por defecto procesa los que ya tienen texto extraído (ultra rápido)
            qs = qs.exclude(extracted_text__isnull=True).exclude(extracted_text="")

        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Reportes a reprocesar: {total:,}\n")

        if total == 0:
            self.stdout.write(self.style.WARNING("No hay reportes que coincidan con los criterios."))
            return

        procesados = 0
        errores = 0
        palabras_pendientes_ws = {}

        if workers > 1:
            import multiprocessing
            self.stdout.write(f"Iniciando procesamiento acelerado con {workers} procesos concurrentes en CPU (contexto fork)...\n")
            items = [
                (
                    r.id,
                    r.file.path if (r.file and os.path.exists(r.file.path)) else None,
                    r.extracted_text,
                    from_file,
                )
                for r in qs
            ]
            reports_dict = {r.id: r for r in qs}

            ctx = multiprocessing.get_context("fork")
            with ctx.Pool(processes=workers) as pool:
                for rep_id, texto_limpio, metricas, conteo, err in pool.imap_unordered(_worker_extract_and_metrics, items, chunksize=1):
                    r = reports_dict[rep_id]
                    try:
                        if err:
                            errores += 1
                            self.stdout.write(self.style.ERROR(f"Error en reporte ID {r.id}: {err}"))
                            continue

                        with transaction.atomic():
                            if not texto_limpio or not texto_limpio.strip():
                                r.extracted_text = ""
                                r.total_words = 0
                                r.unique_words = 0
                                r.total_sentences = 0
                                r.avg_word_length = 0.0
                                r.avg_sentence_length = 0.0
                                r.inflesz_score = 0.0
                                r.total_syllables = 0
                                r.technical_words_count = 0
                                r.save()
                                procesados += 1
                                continue

                            r.extracted_text = texto_limpio
                            r.total_words = metricas.get("total_words", 0)
                            r.unique_words = metricas.get("unique_words", 0)
                            r.total_sentences = metricas.get("total_sentences", 0)
                            r.avg_word_length = metricas.get("avg_word_length", 0)
                            r.avg_sentence_length = metricas.get("avg_sentence_length", 0)
                            r.inflesz_score = metricas.get("inverted_inflesz", 0)
                            r.total_syllables = metricas.get("total_syllables", 0)
                            r.technical_words_count = contar_palabras_tecnicas(
                                texto_limpio, r.year, workspace=r.workspace
                            )
                            r.save()

                            palabras_previas = set(
                                TotalCountReport.objects.filter(report=r).values_list("word", flat=True)
                            )
                            palabras_actuales = set(conteo.keys())
                            palabras_eliminadas = palabras_previas - palabras_actuales
                            if palabras_eliminadas:
                                TotalCountReport.objects.filter(report=r, word__in=palabras_eliminadas).delete()

                            if not palabras_previas:
                                tcr_objs = [
                                    TotalCountReport(report=r, word=palabra, quantity=cantidad)
                                    for palabra, cantidad in conteo.items()
                                ]
                                TotalCountReport.objects.bulk_create(tcr_objs, batch_size=500)
                            else:
                                for palabra, cantidad in conteo.items():
                                    TotalCountReport.objects.update_or_create(
                                        report=r, word=palabra, defaults={"quantity": cantidad}
                                    )

                            todas_afectadas = palabras_previas | palabras_actuales
                            ws_id_rep = r.workspace_id
                            if ws_id_rep not in palabras_pendientes_ws:
                                palabras_pendientes_ws[ws_id_rep] = (r.workspace, set())
                            palabras_pendientes_ws[ws_id_rep][1].update(todas_afectadas)

                            procesados += 1

                            if procesados % 25 == 0 or procesados == total:
                                for ws, palabras_set in palabras_pendientes_ws.values():
                                    if palabras_set:
                                        sincronizar_palabras_total_count(palabras_set, workspace=ws)
                                palabras_pendientes_ws.clear()
                                self.stdout.write(f"  Progreso: {procesados}/{total} reportes reprocesados...")
                    except Exception as e:
                        errores += 1
                        self.stdout.write(self.style.ERROR(f"Error al guardar reporte ID {r.id}: {e}"))
        else:
            for r in qs:
                try:
                    with transaction.atomic():
                        if from_file and r.file and os.path.exists(r.file.path):
                            texto = extraer_texto_pdf_inteligente(r.file.path)
                        else:
                            texto = r.extracted_text

                        if not texto or not texto.strip():
                            r.extracted_text = ""
                            r.total_words = 0
                            r.unique_words = 0
                            r.total_sentences = 0
                            r.avg_word_length = 0.0
                            r.avg_sentence_length = 0.0
                            r.inflesz_score = 0.0
                            r.total_syllables = 0
                            r.technical_words_count = 0
                            r.save()
                            procesados += 1
                            continue

                        # Limpieza estructural
                        texto = limpiar_texto_estructural(texto)
                        r.extracted_text = texto

                        # Métricas de complejidad actualizadas
                        metricas = calcular_metricas_complejidad(texto)
                        r.total_words = metricas.get("total_words", 0)
                        r.unique_words = metricas.get("unique_words", 0)
                        r.total_sentences = metricas.get("total_sentences", 0)
                        r.avg_word_length = metricas.get("avg_word_length", 0)
                        r.avg_sentence_length = metricas.get("avg_sentence_length", 0)
                        r.inflesz_score = metricas.get("inverted_inflesz", 0)
                        r.total_syllables = metricas.get("total_syllables", 0)

                        r.technical_words_count = contar_palabras_tecnicas(
                            texto, r.year, workspace=r.workspace
                        )
                        r.save()

                        # Re-conteo con nuevo motor de palabras
                        palabras_previas = set(
                            TotalCountReport.objects.filter(report=r).values_list("word", flat=True)
                        )
                        conteo = count_words(texto)
                        palabras_actuales = set(conteo.keys())

                        # Eliminar palabras previas que ya no existan
                        palabras_eliminadas = palabras_previas - palabras_actuales
                        if palabras_eliminadas:
                            TotalCountReport.objects.filter(report=r, word__in=palabras_eliminadas).delete()

                        # Actualizar conteos por reporte de forma optimizada
                        if not palabras_previas:
                            tcr_objs = [
                                TotalCountReport(report=r, word=palabra, quantity=cantidad)
                                for palabra, cantidad in conteo.items()
                            ]
                            TotalCountReport.objects.bulk_create(tcr_objs, batch_size=500)
                        else:
                            for palabra, cantidad in conteo.items():
                                TotalCountReport.objects.update_or_create(
                                    report=r, word=palabra, defaults={"quantity": cantidad}
                                )

                        # Acumular palabras afectadas para sincronización por lotes
                        todas_afectadas = palabras_previas | palabras_actuales
                        ws_id = r.workspace_id
                        if ws_id not in palabras_pendientes_ws:
                            palabras_pendientes_ws[ws_id] = (r.workspace, set())
                        palabras_pendientes_ws[ws_id][1].update(todas_afectadas)

                        procesados += 1

                        # Sincronizar TotalCount periódicamente cada 25 reportes para rendimiento óptimo
                        if procesados % 25 == 0:
                            for ws, palabras_set in palabras_pendientes_ws.values():
                                if palabras_set:
                                    sincronizar_palabras_total_count(palabras_set, workspace=ws)
                            palabras_pendientes_ws.clear()
                            self.stdout.write(f"  Progreso: {procesados}/{total} reportes reprocesados...")

                except Exception as e:
                    errores += 1
                    self.stdout.write(self.style.ERROR(f"Error en reporte ID {r.id} ({r.name}): {e}"))

        # Sincronizar palabras residuales pendientes
        for ws, palabras_set in palabras_pendientes_ws.values():
            if palabras_set:
                sincronizar_palabras_total_count(palabras_set, workspace=ws)
        palabras_pendientes_ws.clear()

        self.stdout.write(self.style.SUCCESS(f"\n✓ Reprocesamiento completado: {procesados} exitosos, {errores} errores."))

