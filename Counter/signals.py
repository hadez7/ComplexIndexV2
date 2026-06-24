from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Report, TotalCount, TotalCountReport
import os

@receiver(pre_delete, sender=Report)
def actualizar_totalcount_al_eliminar_reporte(sender, instance, **kwargs):
    print("Signal activado")
    nombre_archivo_real = os.path.basename(instance.file.name)
    print(f"Eliminando conteo de {nombre_archivo_real}...")

    report_counts = TotalCountReport.objects.filter(report=instance)

    for entry in report_counts:
        try:
            total = TotalCount.objects.get(word=entry.word)
            total.quantity -= entry.quantity
            if total.quantity <= 0:
                total.delete()
                print(f"Eliminado TotalCount para {entry.word}")
            else:
                total.save()
                print(f"Actualizado TotalCount para {entry.word}: {total.quantity}")
        except TotalCount.DoesNotExist:
            print(f"No existía TotalCount para {entry.word}, omitiendo...")

    # Eliminar el archivo físico
    if instance.file and instance.file.path:
        try:
            os.remove(instance.file.path)
            print(f"Archivo eliminado: {instance.file.path}")
        except FileNotFoundError:
            print(f"Archivo no encontrado: {instance.file.path}")
        except Exception as e:
            print(f"Error al eliminar archivo: {e}")
