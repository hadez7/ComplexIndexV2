from django.core.management.base import BaseCommand
from django.db import transaction
import os
from Counter.models import Report, TotalCountReport
from Counter.main import count_words, sincronizar_palabras_total_count
from Counter.utils import (
    extraer_texto_pdf_inteligente,
    calcular_metricas_complejidad,
    contar_palabras_tecnicas,
)
from Counter.cleaner import limpiar_texto_estructural


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

    def handle(self, *args, **options):
        ws_id = options["workspace_id"]
        from_file = options["from_file"]
        limit = options["limit"]

        self.stdout.write(self.style.MIGRATE_HEADING("=== REPROCESAMIENTO LINGÜÍSTICO DE REPORTES ==="))

        qs = Report.objects.all().select_related("workspace", "company")
        if ws_id:
            qs = qs.filter(workspace_id=ws_id)

        if not from_file:
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

        for r in qs:
            try:
                with transaction.atomic():
                    if from_file and r.file and os.path.exists(r.file.path):
                        texto = extraer_texto_pdf_inteligente(r.file.path)
                    else:
                        texto = r.extracted_text

                    if not texto or not texto.strip():
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

                    # Actualizar conteos por reporte
                    for palabra, cantidad in conteo.items():
                        TotalCountReport.objects.update_or_create(
                            report=r, word=palabra, defaults={"quantity": cantidad}
                        )

                    # Sincronizar tabla agregada TotalCount
                    todas_afectadas = palabras_previas | palabras_actuales
                    sincronizar_palabras_total_count(todas_afectadas, workspace=r.workspace)

                    procesados += 1
                    if procesados % 25 == 0 or procesados == total:
                        self.stdout.write(f"  Progreso: {procesados}/{total} reportes reprocesados...")

            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(f"Error en reporte ID {r.id} ({r.name}): {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n✓ Reprocesamiento completado: {procesados} exitosos, {errores} errores."))

