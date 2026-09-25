def get_client_ip(request):
    """Obtiene la dirección IP real del cliente."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_user_action(actor, target_username, action, description, target_user=None, details=None, request=None):
    """Crea una entrada en el log de auditoría de usuarios."""
    from .models import UserAuditLog
    ip = get_client_ip(request) if request else None
    return UserAuditLog.objects.create(
        actor=actor if (actor and actor.is_authenticated) else None,
        target_user=target_user,
        target_username=target_username,
        action=action,
        description=description,
        details=details or {},
        ip_address=ip
    )
