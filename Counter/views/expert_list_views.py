import json
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed
from django.contrib.auth.decorators import login_required
from ..models import Expert, ExpertWord
from ..workspace_utils import get_active_workspace
from django.contrib.auth.models import User

SIN_ESPACIO = "No hay un espacio de trabajo activo. Selecciona uno para trabajar con listas."
LISTA_NO_ENCONTRADA = "La lista no existe en el espacio de trabajo activo."


def _espacio_activo_o_error(request):
    """Devuelve el espacio activo o una tupla (None, respuesta_json) si no hay."""
    ws = get_active_workspace(request)
    if not ws:
        return None, JsonResponse({"success": False, "error": SIN_ESPACIO}, status=400)
    return ws, None


@login_required
def create_list(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        expert_id = data.get('expert_id')
        name = data.get('name')
        words = data.get('words', [])

        ws, error = _espacio_activo_o_error(request)
        if error:
            return error

        expert = get_object_or_404(Expert, id=expert_id)

        existing = ExpertWord.objects.filter(
            workspace=ws,
            expert=expert,
            name__iexact=name
        ).exists()

        if existing:
            return JsonResponse({
                "success": False,
                "error": "Ya existe una lista con ese nombre para este experto en este espacio."
            }, status=400)

        new_list = ExpertWord.objects.create(
            workspace=ws,
            expert=expert,
            name=name,
            words=words
        )

        return JsonResponse({
            'success': True,
            'id': new_list.id
        })

    return JsonResponse({'success': False}, status=400)


@login_required
def get_list_json(request, list_id):
    ws, error = _espacio_activo_o_error(request)
    if error:
        return error

    lista = get_object_or_404(ExpertWord, id=list_id, workspace=ws)
    return JsonResponse({
        "id": lista.id,
        "name": lista.name,
        "words": lista.words
    })


@login_required
def update_list(request, list_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    data  = json.loads(request.body)

    ws, error = _espacio_activo_o_error(request)
    if error:
        return error

    try:
        lista = ExpertWord.objects.get(id=list_id, workspace=ws)
    except ExpertWord.DoesNotExist:
        return JsonResponse({"error": LISTA_NO_ENCONTRADA}, status=404)

    # Solo tocar los campos presentes en el JSON -------------------------
    if "name" in data and data["name"] is not None:
        existe = ExpertWord.objects.filter(
            workspace=ws,
            expert=lista.expert,
            name__iexact=data["name"]
        ).exclude(
            id=lista.id
        ).exists()

        if existe:
            return JsonResponse({
                "success": False,
                "error": "Ya existe una lista con ese nombre para este experto en este espacio."
            }, status=400)
        lista.name = data["name"]

    if "words" in data:
        lista.words = data["words"]

    lista.save()
    return JsonResponse({"success": True})


@login_required
def delete_list(request, list_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    ws, error = _espacio_activo_o_error(request)
    if error:
        return error

    try:
        lista = ExpertWord.objects.get(id=list_id, workspace=ws)
        lista.delete()
        return JsonResponse({"success": True})
    except ExpertWord.DoesNotExist:
        return JsonResponse({"error": LISTA_NO_ENCONTRADA}, status=404)


@login_required
def create_expert(request):
    if request.method == "POST":
        data = json.loads(request.body)

        user_id = data.get("user_id")
        profession = data.get("profession")

        user = User.objects.get(id=user_id)

        expert, created = Expert.objects.get_or_create(
            user=user,
            defaults={
                "profession": profession
            }
        )

        return JsonResponse({
            "success": True,
            "created": created
        })

    return JsonResponse({"success": False}, status=400)


@login_required
def expert_list_view(request):
    ws = get_active_workspace(request)

    # Las listas de palabras son estrictamente por espacio de trabajo: si no hay
    # espacio activo, la plantilla verá listas vacías en lugar de las de otros espacios.
    listas_ws = ExpertWord.objects.filter(workspace=ws)

    experts = Expert.objects.prefetch_related(
        Prefetch("word_lists", queryset=listas_ws)
    ).select_related("user", "user__profile")

    expert_users = Expert.objects.values_list(
        "user_id",
        flat=True
    )

    available_users = User.objects.exclude(
        id__in=expert_users
    )

    return render(
        request,
        "expert_lists.html",
        {
            "experts": experts,
            "available_users": available_users,
            "current_workspace": ws,
        }
    )
