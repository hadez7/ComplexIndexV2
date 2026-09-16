from django.db import migrations
from django.contrib.auth.models import Group


def crear_grupos(apps, schema_editor):
    Group.objects.get_or_create(name="Administrador")


def eliminar_grupos(apps, schema_editor):
    Group.objects.filter(name="Administrador").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('User', '0007_alter_userprofile_picture'),
    ]

    operations = [
        migrations.RunPython(crear_grupos, eliminar_grupos),
    ]