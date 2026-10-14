from .workspace_utils import get_active_workspace, get_user_workspaces, is_expert_user


def workspace_context(request):
    """
    Context processor para inyectar el espacio de trabajo activo, la lista
    de espacios de trabajo y si el usuario es perito experto en todas las plantillas.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'current_workspace': None,
            'user_workspaces': [],
            'is_expert_user': False,
        }

    current_ws = get_active_workspace(request)
    workspaces = get_user_workspaces(request.user)

    return {
        'current_workspace': current_ws,
        'user_workspaces': workspaces,
        'is_expert_user': is_expert_user(request.user),
    }
