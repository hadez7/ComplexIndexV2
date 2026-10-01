from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import openpyxl
from Counter.models import Company, Province, Workspace


class Command(BaseCommand):
    help = 'Importar empresas desde el archivo Empresas.xlsx'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Empresas.xlsx',
            help='Ruta del archivo xlsx a importar (default: Empresas.xlsx)'
        )
        parser.add_argument(
            '--workspace',
            type=int,
            required=True,
            help='ID del espacio de trabajo donde se crearán las empresas (obligatorio)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options['file']

        try:
            workspace = Workspace.objects.get(pk=options['workspace'])
        except Workspace.DoesNotExist:
            raise CommandError(f"No existe el espacio de trabajo id={options['workspace']}")
        if Workspace.objects.filter(is_archived=True, pk=workspace.pk).exists():
            raise CommandError(f"El espacio '{workspace.name}' está archivado.")

        self.stdout.write(f"Espacio de trabajo: {workspace.name} (id={workspace.pk})")
        self.stdout.write(f"Leyendo archivo: {file_path}")
        
        try:
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active
            
            total_rows = ws.max_row - 1  # Excluir header
            created = 0
            updated = 0
            errors = 0
            
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 1):
                try:
                    provincia_name, ruc, empresa_name = row[0], str(int(row[1])), row[2]
                    
                    # Obtener o crear la provincia
                    provincia, _ = Province.objects.get_or_create(name=provincia_name)
                    
                    # Crear o actualizar la empresa DENTRO del espacio indicado.
                    # El RUC solo es único por espacio, así que hay que filtrar por workspace:
                    # si no, se editarían empresas de otros espacios.
                    company, created_flag = Company.objects.get_or_create(
                        workspace=workspace,
                        ruc=ruc,
                        defaults={'name': empresa_name, 'province': provincia}
                    )
                    
                    if created_flag:
                        created += 1
                    else:
                        # Actualizar si ya existe
                        company.name = empresa_name
                        company.province = provincia
                        company.save()
                        updated += 1
                    
                    # Mostrar progreso
                    if row_idx % 50 == 0:
                        self.stdout.write(f"Procesados {row_idx}/{total_rows}...")
                        
                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.WARNING(f"Error en fila {row_idx + 1}: {str(e)}")
                    )
                    continue
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Importación completada!\n"
                    f"  - Empresas creadas: {created}\n"
                    f"  - Empresas actualizadas: {updated}\n"
                    f"  - Errores: {errors}\n"
                    f"  - Total: {created + updated}"
                )
            )
            
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f"❌ Archivo no encontrado: {file_path}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error: {str(e)}")
            )
