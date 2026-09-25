from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, default='profile_pics/default.jpg')
    creation_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False, verbose_name="Dado de baja")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de baja")

    def __str__(self):
        return self.user.username


class Expert(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='expert_profile')
    profession = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.user.username


class UserAuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Creación de usuario'),
        ('UPDATE', 'Edición de usuario'),
        ('SOFT_DELETE', 'Baja lógica (Soft Delete)'),
        ('RESTORE', 'Reactivación de cuenta'),
        ('TOGGLE_ACTIVE', 'Cambio de estado activo/inactivo'),
        ('ROLE_CHANGE', 'Cambio de rol'),
        ('EXPERT_CHANGE', 'Asignación de especialidad'),
        ('PASSWORD_CHANGE', 'Cambio de contraseña'),
        ('LOGIN', 'Inicio de sesión'),
    ]

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions_performed',
        verbose_name="Realizado por"
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_records',
        verbose_name="Usuario afectado"
    )
    target_username = models.CharField(max_length=150, verbose_name="Nombre de usuario afectado")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name="Acción")
    description = models.CharField(max_length=255, verbose_name="Descripción")
    details = models.JSONField(default=dict, blank=True, verbose_name="Detalles técnicos")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Registro de auditoría de usuario"
        verbose_name_plural = "Registros de auditoría de usuarios"

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.get_action_display()} - {self.target_username}"
