from .workspace_utils import get_active_workspace, get_user_workspaces


def workspace_context(request):
    """
    Context processor para inyectar el espacio de trabajo activo y la lista
    de espacios de trabajo en todas las plantillas.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'current_workspace': None,
            'user_workspaces': [],
        }

    current_ws = get_active_workspace(request)
    workspaces = get_user_workspaces(request.user)

    return {
        'current_workspace': current_ws,
        'user_workspaces': workspaces,
    }
