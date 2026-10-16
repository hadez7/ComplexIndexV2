from django.core.management.base import BaseCommand
from django.db.models import Count
from Counter.models import Report, Company, TotalCount, TotalCountReport


class Command(BaseCommand):
    help = "Depura reportes duplicados por (espacio, empresa, año), conservando el que contiene más datos procesados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la depuración sin realizar cambios en la base de datos.",
        )
        parser.add_argument(
            "--company",
            type=str,
            default=None,
            help="Filtra por nombre o RUC de empresa específica (ej: Armacar).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        company_query = options["company"]

        self.stdout.write(self.style.MIGRATE_HEADING("=== DEPURACIÓN DE REPORTES DUPLICADOS ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO SIMULACIÓN (--dry-run): No se borrarán registros."))

        # Buscar combinaciones duplicadas
        dups_qs = Report.objects.values("workspace", "company", "year").annotate(c=Count("id")).filter(c__gt=1)
        if company_query:
            matching_company_ids = Company.objects.filter(name__icontains=company_query).values_list("id", flat=True)
            dups_qs = dups_qs.filter(company_id__in=matching_company_ids)

        total_dups = dups_qs.count()
        self.stdout.write(f"Combinaciones (empresa, año) con duplicados: {total_dups}\n")

        if total_dups == 0:
            self.stdout.write(self.style.SUCCESS("No se encontraron reportes duplicados."))
            return

        def score_report(r):
            has_text = 1 if (r.extracted_text and len(r.extracted_text.strip()) > 0) else 0
            words = r.total_words or 0
            has_inflesz = 1 if (r.inflesz_score is not None and r.inflesz_score > 0) else 0
            return (has_text, words, has_inflesz, -r.id)

        eliminados_count = 0
        palabras_descontadas = 0

        for item in dups_qs:
            reports = list(Report.objects.filter(
                workspace_id=item["workspace"],
                company_id=item["company"],
                year=item["year"],
            ).select_related("company"))

            if len(reports) <= 1:
                continue

            sorted_reports = sorted(reports, key=score_report, reverse=True)
            best_report = sorted_reports[0]
            to_delete = sorted_reports[1:]

            company_name = best_report.company.name if best_report.company else "Sin empresa"
            self.stdout.write(f"Empresa: {company_name} | Año: {best_report.year}")
            self.stdout.write(f"  -> Conservado: ID {best_report.id} (Palabras: {best_report.total_words or 0}, Archivo: {best_report.file.name})")

            for rep in to_delete:
                self.stdout.write(self.style.WARNING(
                    f"  -> A eliminar: ID {rep.id} (Palabras: {rep.total_words or 0}, Archivo: {rep.file.name})"
                ))
                eliminados_count += 1
                if rep.total_words:
                    palabras_descontadas += rep.total_words

                if not dry_run:
                    # report.delete() activa el signal de Counter.signals para descontar TotalCount y TotalCountReport
                    rep.delete()

        estado = "SIMULACIÓN COMPLETADA" if dry_run else "PROCESO FINALIZADO"
        self.stdout.write(self.style.SUCCESS(
            f"\n{estado}. Total de reportes duplicados {'identificados' if dry_run else 'eliminados'}: {eliminados_count}"
        ))
        if palabras_descontadas > 0:
            self.stdout.write(f"Palabras redundantes {'identificadas' if dry_run else 'depuradas del cómputo'}: {palabras_descontadas:,}")

