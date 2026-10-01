from django.db import migrations


def forwards_func(apps, schema_editor):
    Workspace = apps.get_model('Counter', 'Workspace')
    WorkspaceMembership = apps.get_model('Counter', 'WorkspaceMembership')
    User = apps.get_model('auth', 'User')
    Company = apps.get_model('Counter', 'Company')
    Report = apps.get_model('Counter', 'Report')
    TotalCount = apps.get_model('Counter', 'TotalCount')
    ExpertWord = apps.get_model('Counter', 'ExpertWord')

    # Solo migramos si existen datos
    if Company.objects.exists() or Report.objects.exists():
        first_admin = User.objects.filter(is_superuser=True).first() or User.objects.first()

        default_workspace, created = Workspace.objects.get_or_create(
            name="Informes Corporativos",
            defaults={
                "description": "Espacio de trabajo inicial migrado con todos los documentos corporativos, empresas y métricas existentes.",
                "project_type": "Corporativo",
                "color": "blue",
                "icon": "building",
                "created_by": first_admin,
            }
        )

        # Vincular a todos los usuarios existentes al espacio por defecto
        for u in User.objects.all():
            role = 'admin' if (u.is_superuser or u.is_staff) else 'editor'
            WorkspaceMembership.objects.get_or_create(
                workspace=default_workspace,
                user=u,
                defaults={'role': role}
            )

        # Asignar masivamente registros existentes sin espacio al espacio por defecto
        num_companies = Company.objects.filter(workspace__isnull=True).update(workspace=default_workspace)
        num_reports = Report.objects.filter(workspace__isnull=True).update(workspace=default_workspace)
        num_totalcount = TotalCount.objects.filter(workspace__isnull=True).update(workspace=default_workspace)
        num_expertwords = ExpertWord.objects.filter(workspace__isnull=True).update(workspace=default_workspace)

        print(f"\n[Migración completada] Espacio '{default_workspace.name}':")
        print(f"  - {num_companies} empresas asignadas.")
        print(f"  - {num_reports} reportes asignados.")
        print(f"  - {num_totalcount} palabras de conteo consolidado asignadas.")
        print(f"  - {num_expertwords} listas de palabras técnicas asignadas.")


def backwards_func(apps, schema_editor):
    # La reversión no destruye los datos de las tablas originales, solo limpia la asignación
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Counter', '0018_alter_company_ruc_alter_report_company_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
