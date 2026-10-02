import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import ProtectedError, Q, Sum
from django.http import JsonResponse, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from ..models import Workspace, WorkspaceMembership, Report, Company, TotalCount
from ..workspace_utils import get_user_workspaces, get_active_workspace, set_active_workspace


def _es_admin_del_espacio(request, workspace):
    """staff/superuser o rol 'admin' en el espacio."""
    return (
        request.user.is_superuser
        or request.user.is_staff
        or WorkspaceMembership.objects.filter(
            workspace=workspace, user=request.user, role="admin"
        ).exists()
    )


def _roles_validos():
    return dict(WorkspaceMembership.ROLE_CHOICES)


def _datos_miembros(workspace):
    """
    Miembros del espacio para la pantalla de gestión.

    El creador aparece siempre como administrador (aunque su membresía se haya
    creado antes de existir esta tabla) y nunca se puede quitar a sí mismo:
    así el espacio nunca se queda sin alguien que pueda gestionarlo.
    """
    admins = list(
        workspace.memberships.filter(role="admin").values_list("user_id", flat=True)
    )
    creador_id = workspace.created_by_id
    if creador_id and creador_id not in admins:
        admins.append(creador_id)

    filas = []
    vistos = set()

    for m in workspace.memberships.select_related("user").order_by("user__username"):
        es_creador = m.user_id == creador_id
        ultimo_admin = m.role == "admin" and len(admins) <= 1
        filas.append({
            "user_id": m.user_id,
            "username": m.user.username,
            "email": m.user.email,
            "role": m.role,
            "role_display": m.get_role_display(),
            "joined_at": m.joined_at.strftime("%d/%m/%Y"),
            "es_creador": es_creador,
            "puede_eliminar": not es_creador and not ultimo_admin,
            "puede_cambiar_rol": not es_creador and not ultimo_admin,
        })
        vistos.add(m.user_id)

    if creador_id and creador_id not in vistos:
        u = workspace.created_by
        filas.insert(0, {
            "user_id": u.id,
            "username": u.username,
            "email": u.email,
            "role": "admin",
            "role_display": dict(WorkspaceMembership.ROLE_CHOICES)["admin"],
            "joined_at": "",
            "es_creador": True,
            "puede_eliminar": False,
            "puede_cambiar_rol": False,
        })

    return filas


def _espacio_tiene_contenido(workspace):
    """Un espacio 'no vacío' tiene reportes o empresas. Los conteos y las listas derivan de ellos."""
    return workspace.reports.exists() or workspace.companies.exists()


def _es_unico_activo(workspace):
    """True si es el único espacio no archivado: no se puede archivar ni eliminar."""
    return (
        not workspace.is_archived
        and Workspace.objects.filter(is_archived=False).count() <= 1
    )


@login_required
def workspace_list_view(request):
    """
    Vista principal de gestión de espacios de trabajo:
    Muestra la cuadrícula de espacios, estadísticas individuales, y modales de acción.
    """
    search = request.GET.get("q", "").strip()
    # En la pantalla de gestión se muestran también los archivados (con su distintivo
    # y la opción de restaurarlos); get_user_workspaces los excluye por defecto para
    # que no se puedan activar ni aparezcan en el selector de la barra superior.
    workspaces_qs = get_user_workspaces(request.user, include_archived=True)

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

        can_manage = _es_admin_del_espacio(request, ws)
        members = _datos_miembros(ws)

        workspaces_data.append({
            "workspace": ws,
            "reports_count": rep_count,
            "companies_count": comp_count,
            "total_words": words_sum,
            "is_active": (active_ws and ws.id == active_ws.id),
            # Solo el admin del espacio (o el staff) gestiona sus miembros.
            "can_manage": can_manage,
            "members_count": len(members),
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
    if not _es_admin_del_espacio(request, workspace):
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
def workspace_archive_view(request, workspace_id):
    """
    Archiva o restaura un espacio de trabajo.
    Archivar es la forma segura de "quitar" un espacio: oculta sus datos sin borrar nada.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    workspace = get_object_or_404(Workspace, id=workspace_id)

    if not _es_admin_del_espacio(request, workspace):
        return JsonResponse({"error": _("No tienes permisos para modificar este espacio.")}, status=403)

    # Archivar: nunca el último espacio activo (se dejaría el sistema sin ningún espacio).
    if not workspace.is_archived and _es_unico_activo(workspace):
        return JsonResponse({
            "error": _("No puedes archivar el único espacio de trabajo activo.")
        }, status=400)

    workspace.is_archived = not workspace.is_archived
    workspace.save(update_fields=["is_archived"])

    # Un espacio archivado no puede seguir siendo el activo.
    if workspace.is_archived and request.session.get("active_workspace_id") == workspace.id:
        request.session.pop("active_workspace_id", None)

    if workspace.is_archived:
        message = _("El espacio de trabajo '%s' fue archivado. Puedes restaurarlo cuando quieras.") % workspace.name
    else:
        message = _("El espacio de trabajo '%s' fue restaurado.") % workspace.name

    return JsonResponse({"success": True, "is_archived": workspace.is_archived, "message": message})


@login_required
def workspace_delete_view(request, workspace_id):
    """
    Elimina un espacio de trabajo SOLO si está vacío y el usuario es administrador.
    Para espacios con contenido la única opción es archivarlos (borrado reversible).
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    workspace = get_object_or_404(Workspace, id=workspace_id)

    if not _es_admin_del_espacio(request, workspace):
        return JsonResponse({"error": _("No tienes permisos para eliminar este espacio.")}, status=403)

    # Validar que no sea el único espacio existente para no dejar el sistema vacío
    if _es_unico_activo(workspace):
        return JsonResponse({"error": _("No puedes eliminar el único espacio de trabajo disponible.")}, status=400)

    # Contenido = intocable. Se protege aquí y además a nivel de modelo con PROTECT.
    if _espacio_tiene_contenido(workspace):
        return JsonResponse({
            "error": _("Este espacio tiene reportes o empresas, por lo que no se puede eliminar. "
                       "Archívalo para ocultarlo sin perder ningún dato.")
        }, status=400)

    # Si era el activo, limpiar la sesión
    if request.session.get("active_workspace_id") == workspace.id:
        request.session.pop("active_workspace_id", None)

    workspace_name = workspace.name
    try:
        workspace.delete()
    except ProtectedError:
        # Doble cinturón: aunque la comprobación anterior falle, el modelo no deja
        # borrar un espacio referenciado (evita que se arrastren reportes y PDFs).
        return JsonResponse({
            "error": _("Este espacio tiene reportes o empresas, por lo que no se puede eliminar. "
                       "Archívalo para ocultarlo sin perder ningún dato.")
        }, status=400)

    messages.info(request, _("El espacio de trabajo '%s' fue eliminado.") % workspace_name)
    return JsonResponse({"success": True})


# --------------------------------- MIEMBROS DEL ESPACIO ---------------------------------
# Un usuario nuevo no ve nada hasta que un admin del espacio lo añade desde aquí.

def _error_sin_permisos():
    return JsonResponse(
        {"error": _("No tienes permisos para gestionar los miembros de este espacio.")},
        status=403,
    )


def _espacio_o_error(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id)
    if not _es_admin_del_espacio(request, workspace):
        return None, _error_sin_permisos()
    return workspace, None


def _body(request):
    if request.content_type == "application/json":
        try:
            return json.loads(request.body), None
        except Exception:
            return None, JsonResponse({"error": _("Cuerpo JSON inválido.")}, status=400)
    return request.POST, None


def _user_id(data):
    """'user_id' puede llegar como texto (form) o número (JSON)."""
    try:
        return int(data.get("user_id"))
    except (TypeError, ValueError):
        return None


@login_required
def workspace_members_view(request, workspace_id):
    """Lista de miembros y de usuarios aún no añadidos (rellena el modal)."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    workspace, error = _espacio_o_error(request, workspace_id)
    if error:
        return error

    miembros = _datos_miembros(workspace)

    disponibles = [
        {"id": u.id, "username": u.username, "email": u.email}
        for u in User.objects.filter(is_active=True)
        .exclude(id__in=[m["user_id"] for m in miembros])
        .order_by("username")
    ]

    return JsonResponse({
        "success": True,
        "workspace": {"id": workspace.id, "name": workspace.name},
        "members": miembros,
        "available_users": disponibles,
        "roles": [
            {"value": value, "label": label}
            for value, label in WorkspaceMembership.ROLE_CHOICES
        ],
    })


@login_required
def workspace_members_add_view(request, workspace_id):
    """Añade un usuario al espacio: es la 'aprobación' que da acceso a su trabajo."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    workspace, error = _espacio_o_error(request, workspace_id)
    if error:
        return error

    data, error = _body(request)
    if error:
        return error

    user_id = _user_id(data)
    role = (data.get("role") or "viewer").strip()

    if user_id is None:
        return JsonResponse({"error": _("Usuario no indicado.")}, status=400)
    if role not in _roles_validos():
        return JsonResponse({"error": _("Rol no válido.")}, status=400)

    target = User.objects.filter(id=user_id, is_active=True).first()
    if target is None:
        return JsonResponse({"error": _("Usuario no encontrado.")}, status=404)

    if workspace.memberships.filter(user=target).exists():
        return JsonResponse(
            {"error": _("Ese usuario ya es miembro de este espacio.")}, status=400
        )

    WorkspaceMembership.objects.create(workspace=workspace, user=target, role=role)

    return JsonResponse({
        "success": True,
        "message": _("%s ahora tiene acceso a este espacio.") % target.username,
        "members": _datos_miembros(workspace),
    })


@login_required
def workspace_members_remove_view(request, workspace_id):
    """Quita a un usuario del espacio: deja de ver todos sus datos."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    workspace, error = _espacio_o_error(request, workspace_id)
    if error:
        return error

    data, error = _body(request)
    if error:
        return error

    miembros = _datos_miembros(workspace)
    actual = next((m for m in miembros if m["user_id"] == _user_id(data)), None)
    if actual is None:
        return JsonResponse({"error": _("Ese usuario no es miembro de este espacio.")}, status=404)
    if not actual["puede_eliminar"]:
        return JsonResponse({
            "error": _("No se puede quitar a este usuario: es el creador o el "
                       "último administrador del espacio.")
        }, status=400)

    WorkspaceMembership.objects.filter(
        workspace=workspace, user_id=actual["user_id"]
    ).delete()

    return JsonResponse({
        "success": True,
        "message": _("%s dejó de tener acceso a este espacio.") % actual["username"],
        "members": _datos_miembros(workspace),
    })


@login_required
def workspace_members_role_view(request, workspace_id):
    """Cambia el rol de un miembro (admin, editor/auditor, lector)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    workspace, error = _espacio_o_error(request, workspace_id)
    if error:
        return error

    data, error = _body(request)
    if error:
        return error

    role = (data.get("role") or "").strip()
    if role not in _roles_validos():
        return JsonResponse({"error": _("Rol no válido.")}, status=400)

    miembros = _datos_miembros(workspace)
    actual = next((m for m in miembros if m["user_id"] == _user_id(data)), None)
    if actual is None:
        return JsonResponse({"error": _("Ese usuario no es miembro de este espacio.")}, status=404)
    if not actual["puede_cambiar_rol"]:
        return JsonResponse({
            "error": _("No se puede cambiar el rol de este usuario: es el creador "
                       "o el último administrador del espacio.")
        }, status=400)

    WorkspaceMembership.objects.filter(
        workspace=workspace, user_id=actual["user_id"]
    ).update(role=role)

    return JsonResponse({
        "success": True,
        "message": _("Rol de %s actualizado.") % actual["username"],
        "members": _datos_miembros(workspace),
    })
