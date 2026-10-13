from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from Counter.models import TotalCountReport, TotalCount, Workspace
from Counter.stopwords import STOPWORDS_ES
from Counter.cleaner import procesar_palabra_individual, quitar_tildes, extraer_palabras_limpias


class Command(BaseCommand):
    help = (
        "Sanea la base de datos eliminando pseudopalabras, ruido OCR, números romanos y palabras fusionadas "
        "(ej: aacccciio, abrildel, etc.), sincronizando la tabla TotalCount matemáticamente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la depuración sin realizar cambios en la base de datos.",
        )
        parser.add_argument(
            "--workspace-id",
            type=int,
            default=None,
            help="ID del espacio de trabajo a sanear (por defecto sanea todos).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        ws_id = options["workspace_id"]

        stopwords_norm = set(quitar_tildes(p) for p in STOPWORDS_ES)

        self.stdout.write(self.style.MIGRATE_HEADING("=== SANEAMIENTO Y LIMPIEZA LÉXICA DE PALABRAS ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO SIMULACIÓN (--dry-run): No se modificarán datos."))

        tc_inicial = TotalCount.objects.count()
        tcr_inicial = TotalCountReport.objects.count()

        self.stdout.write(f"Registros iniciales en TotalCount: {tc_inicial:,}")
        self.stdout.write(f"Registros iniciales en TotalCountReport: {tcr_inicial:,}\n")

        # Filtrar queryset
        tcr_qs = TotalCountReport.objects.select_related("report__workspace")
        if ws_id:
            tcr_qs = tcr_qs.filter(report__workspace_id=ws_id)

        # Analizar palabras únicas en TotalCountReport
        distinct_words = list(tcr_qs.values_list("word", flat=True).distinct())
        self.stdout.write(f"Vocabulario único a evaluar: {len(distinct_words):,} palabras...")

        palabras_a_eliminar = set()
        palabras_a_mapear = {}  # palabra_original -> palabra_corregida

        for w in distinct_words:
            res = procesar_palabra_individual(w, stopwords_norm)
            if not res:
                palabras_a_eliminar.add(w)
            elif len(res) == 1 and res[0] != w:
                palabras_a_mapear[w] = res[0]
            elif len(res) > 1:
                # Caso de sufijo despegado (ej. abrildel -> abril)
                palabras_a_mapear[w] = res[0]

        self.stdout.write(f"-> Palabras basura a eliminar directamente: {len(palabras_a_eliminar):,}")
        self.stdout.write(f"-> Palabras con corrección léxica a fusionar: {len(palabras_a_mapear):,}")
        self.stdout.write(f"-> Palabras legítimas preservadas intactas: {len(distinct_words) - len(palabras_a_eliminar) - len(palabras_a_mapear):,}\n")

        # Muestra de ejemplos detectados
        if palabras_a_eliminar:
            muestra_eliminar = list(palabras_a_eliminar)[:12]
            self.stdout.write(f"Ejemplos a eliminar: {', '.join(muestra_eliminar)}")
        if palabras_a_mapear:
            muestra_mapear = [f"{k} -> {v}" for k, v in list(palabras_a_mapear.items())[:10]]
            self.stdout.write(f"Ejemplos a corregir: {', '.join(muestra_mapear)}\n")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Simulación completada. Ejecuta sin '--dry-run' para aplicar los cambios."))
            return

        # Aplicar depuración real en transacción
        self.stdout.write("Aplicando depuración en base de datos...")
        afectadas_por_ws = {}  # ws_id -> set(palabras)

        with transaction.atomic():
            # 1. Purgar palabras basura
            if palabras_a_eliminar:
                # Recopilar workspaces afectados
                for t in tcr_qs.filter(word__in=palabras_a_eliminar).values("report__workspace_id", "word"):
                    w_ws = t["report__workspace_id"]
                    if w_ws:
                        afectadas_por_ws.setdefault(w_ws, set()).add(t["word"])

                tcr_qs.filter(word__in=palabras_a_eliminar).delete()
                self.stdout.write(self.style.SUCCESS(f"✓ Registros de palabras basura eliminados de TotalCountReport."))

            # 2. Corregir y fusionar palabras mapeadas
            registros_fusionados = 0
            for orig_word, clean_word in palabras_a_mapear.items():
                coincidencias = list(tcr_qs.filter(word=orig_word).select_related("report"))
                for reg in coincidencias:
                    ws = reg.report.workspace_id
                    if ws:
                        afectadas_por_ws.setdefault(ws, set()).add(orig_word)
                        afectadas_por_ws.setdefault(ws, set()).add(clean_word)

                    # Buscar o crear destino
                    destino, creado = TotalCountReport.objects.get_or_create(
                        report=reg.report,
                        word=clean_word,
                        defaults={"quantity": reg.quantity}
                    )
                    if not creado:
                        destino.quantity += reg.quantity
                        destino.save(update_fields=["quantity"])

                    reg.delete()
                    registros_fusionados += 1

            self.stdout.write(self.style.SUCCESS(f"✓ {registros_fusionados:,} registros fusionados y corregidos hacia vocabulario válido."))

            # 3. Sincronizar TotalCount de forma exacta por espacio de trabajo
            self.stdout.write("Sincronizando tabla agregada TotalCount...")
            workspaces_a_sincronizar = Workspace.objects.filter(id__in=afectadas_por_ws.keys()) if not ws_id else Workspace.objects.filter(id=ws_id)

            for ws in workspaces_a_sincronizar:
                palabras_ws = afectadas_por_ws.get(ws.id, set())
                if not palabras_ws:
                    continue

                palabras_lista = list(palabras_ws)
                chunk_size = 500
                for i in range(0, len(palabras_lista), chunk_size):
                    chunk = palabras_lista[i:i + chunk_size]
                    sumas = (
                        TotalCountReport.objects.filter(report__workspace=ws, word__in=chunk)
                        .values("word")
                        .annotate(total=Sum("quantity"))
                    )
                    totales_dict = {item["word"]: item["total"] for item in sumas}

                    for p in chunk:
                        tot = totales_dict.get(p, 0)
                        if tot > 0:
                            TotalCount.objects.update_or_create(
                                workspace=ws,
                                word=p,
                                defaults={"quantity": tot}
                            )
                        else:
                            TotalCount.objects.filter(workspace=ws, word=p).delete()

            # 4. Eliminar huérfanos residuales en TotalCount que ya no tengan ningún TotalCountReport
            # (limpia cualquier residuo antiguo previo a los espacios de trabajo)
            total_count_qs = TotalCount.objects.all() if not ws_id else TotalCount.objects.filter(workspace_id=ws_id)
            palabras_con_reporte = set(TotalCountReport.objects.values_list("word", flat=True).distinct())
            huerfanos = total_count_qs.exclude(word__in=palabras_con_reporte)
            cant_huerfanos = huerfanos.count()
            if cant_huerfanos > 0:
                huerfanos.delete()
                self.stdout.write(f"✓ {cant_huerfanos:,} palabras huérfanas purgadas de TotalCount.")

        tc_final = TotalCount.objects.count()
        tcr_final = TotalCountReport.objects.count()

        self.stdout.write(self.style.SUCCESS("\n=== SANEAMIENTO COMPLETADO EXITOSAMENTE ==="))
        self.stdout.write(f"TotalCount:       {tc_inicial:,} -> {tc_final:,} (Reducción de {tc_inicial - tc_final:,} registros inválidos)")
        self.stdout.write(f"TotalCountReport: {tcr_inicial:,} -> {tcr_final:,}")

