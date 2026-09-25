from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from .models import UserProfile, UserAuditLog
from .utils import get_client_ip


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    elif hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    UserAuditLog.objects.create(
        actor=user,
        target_user=user,
        target_username=user.username,
        action='LOGIN',
        description=f"Inicio de sesión exitoso del usuario '{user.username}'.",
        details={"username": user.username, "email": user.email},
        ip_address=ip
    )
