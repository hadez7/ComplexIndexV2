from django.db.models import Q
from .models import Workspace, WorkspaceMembership


def get_user_workspaces(user):
    """
    Retorna los espacios de trabajo a los que el usuario tiene acceso.
    Los administradores/staff tienen acceso a todos los espacios activos.
    """
    if not user.is_authenticated:
        return Workspace.objects.none()

    if user.is_superuser or user.is_staff:
        return Workspace.objects.filter(is_archived=False).order_by('-created_at')

    return Workspace.objects.filter(
        Q(memberships__user=user) | Q(created_by=user),
        is_archived=False
    ).distinct().order_by('-created_at')


def get_active_workspace(request):
    """
    Determina y retorna el espacio de trabajo activo actual para el usuario.
    Si hay uno guardado en sesión y es válido para el usuario, lo utiliza.
    Si no, selecciona el primero disponible y lo guarda en sesión.
    """
    if not request.user.is_authenticated:
        return None

    user_workspaces = get_user_workspaces(request.user)
    if not user_workspaces.exists():
        return None

    workspace_id = request.session.get("active_workspace_id")
    if workspace_id:
        active_ws = user_workspaces.filter(id=workspace_id).first()
        if active_ws:
            return active_ws

    # Fallback al primer espacio disponible
    first_ws = user_workspaces.first()
    if first_ws:
        request.session["active_workspace_id"] = first_ws.id
        return first_ws

    return None


def set_active_workspace(request, workspace_id):
    """
    Establece el espacio de trabajo activo en la sesión del usuario si tiene permisos.
    """
    user_workspaces = get_user_workspaces(request.user)
    target_ws = user_workspaces.filter(id=workspace_id).first()
    if target_ws:
        request.session["active_workspace_id"] = target_ws.id
        return target_ws
    return None
