import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from ..models import Workspace, WorkspaceMembership, Report, Company, TotalCount
from ..workspace_utils import get_user_workspaces, get_active_workspace, set_active_workspace


@login_required
def workspace_list_view(request):
    """
    Vista principal de gestión de espacios de trabajo:
    Muestra la cuadrícula de espacios, estadísticas individuales, y modales de acción.
    """
    search = request.GET.get("q", "").strip()
    workspaces_qs = get_user_workspaces(request.user)

    if search:
        workspaces_qs = workspaces_qs.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
            | Q(project_type__icontains=search)
        )

    active_ws = get_active_workspace(request)

    workspaces_data = []
    for ws in workspaces_qs:
        rep_count = ws.reports.count()
        comp_count = ws.companies.count()
        words_sum = ws.reports.aggregate(Sum("total_words"))["total_words__sum"] or 0

        workspaces_data.append({
            "workspace": ws,
            "reports_count": rep_count,
            "companies_count": comp_count,
            "total_words": words_sum,
            "is_active": (active_ws and ws.id == active_ws.id),
        })

    context = {
        "workspaces_data": workspaces_data,
        "active_workspace": active_ws,
        "search": search,
        "total_workspaces": len(workspaces_data),
    }
    return render(request, "workspaces.html", context)


@login_required
def workspace_create_view(request):
    """
    Crea un nuevo espacio de trabajo aislado.
    Acepta tanto JSON (para modales AJAX) como envío tradicional POST.
    """
    if request.method != "POST":
        return JsonResponse({"error": _("Método no permitido")}, status=405)

    is_json = request.content_type == "application/json"
    if is_json:
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": _("Cuerpo JSON inválido")}, status=400)
    else:
        data = request.POST

    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    project_type = data.get("project_type", "").strip()
    color = data.get("color", "blue").strip()
    icon = data.get("icon", "folder").strip()

    if not name:
        if is_json:
            return JsonResponse({"errors": {"name": [_("El nombre del espacio es obligatorio.")]}}, status=400)
        messages.error(request, _("El nombre del espacio es obligatorio."))
        return redirect("workspaces_list")

    # Crear el espacio
    workspace = Workspace.objects.create(
        name=name,
        description=description,
        project_type=project_type,
        color=color,
        icon=icon,
        created_by=request.user
    )

    # Asignar membresía de administrador al creador
    WorkspaceMembership.objects.create(
        workspace=workspace,
        user=request.user,
        role="admin"
    )

    # Establecer como espacio activo
    request.session["active_workspace_id"] = workspace.id

    if is_json:
        return JsonResponse({
            "success": True,
            "id": workspace.id,
            "name": workspace.name,
            "project_type": workspace.project_type,
            "message": _("Espacio de trabajo creado exitosamente.")
        })

    messages.success(request, _("Espacio de trabajo '%s' creado y seleccionado.") % workspace.name)
    return redirect("panel")


@login_required
def workspace_select_view(request, workspace_id):
    """
    Cambia el espacio de trabajo activo y redirige al panel o a la página previa.
    """
    selected = set_active_workspace(request, workspace_id)
    if not selected:
        messages.error(request, _("No tienes acceso a este espacio de trabajo."))
        return redirect("workspaces_list")

    next_url = request.GET.get("next") or request.POST.get("next")
    # Validar que next_url sea interna y segura
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)

    messages.success(request, _("Cambiado al espacio: %s") % selected.name)
    return redirect("panel")


@login_required
def workspace_update_view(request, workspace_id):
    """
    Actualiza la información de un espacio de trabajo.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)

    # Validar permisos: staff, superuser, o admin del workspace
    is_admin = request.user.is_superuser or request.user.is_staff or \
        WorkspaceMembership.objects.filter(workspace=workspace, user=request.user, role="admin").exists()

    if not is_admin:
        return JsonResponse({"error": _("No tienes permisos para editar este espacio.")}, status=403)

    is_json = request.content_type == "application/json"
    if is_json:
        data = json.loads(request.body)
    else:
        data = request.POST

    name = data.get("name", "").strip()
    if not name:
        return JsonResponse({"errors": {"name": [_("El nombre no puede estar vacío.")]}}, status=400)

    workspace.name = name
    workspace.description = data.get("description", "").strip()
    workspace.project_type = data.get("project_type", "").strip()
    workspace.color = data.get("color", workspace.color).strip()
    workspace.icon = data.get("icon", workspace.icon).strip()
    workspace.save()

    return JsonResponse({
        "success": True,
        "message": _("Espacio de trabajo actualizado con éxito.")
    })


@login_required
def workspace_delete_view(request, workspace_id):
    """
    Elimina o archiva un espacio de trabajo si el usuario tiene rol de administrador.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)

    is_admin = request.user.is_superuser or request.user.is_staff or \
        WorkspaceMembership.objects.filter(workspace=workspace, user=request.user, role="admin").exists()

    if not is_admin:
        return JsonResponse({"error": _("No tienes permisos para eliminar este espacio.")}, status=403)

    # Validar que no sea el único espacio existente para no dejar el sistema vacío
    if Workspace.objects.filter(is_archived=False).count() <= 1:
        return JsonResponse({"error": _("No puedes eliminar el único espacio de trabajo disponible.")}, status=400)

    # Si era el activo, limpiar la sesión
    if request.session.get("active_workspace_id") == workspace.id:
        request.session.pop("active_workspace_id", None)

    workspace_name = workspace.name
    workspace.delete()

    messages.info(request, _("El espacio de trabajo '%s' fue eliminado.") % workspace_name)
    return JsonResponse({"success": True})
