import os
import json
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.conf import settings
from django.db import IntegrityError
from ..models import Company
from ..forms import IndividualReportUploadForm, ZipUploadForm, ComparativeAnalysisForm
from ..main import process_report, process_zip
from ..models import TotalCountReport
from ..models import Report
from User.models import Expert

# * ---------------------------------------- VISTAS GENERALES ----------------------------------------
def index_view(request):
    return render(request, "index.html")


@login_required
def panel_view(request):
    return render(request, "panel.html")


@login_required
def upload_view(request):
    individual_form = IndividualReportUploadForm()
    zip_form = ZipUploadForm()
    companies = Company.objects.all()

    if request.method == "POST":
        if "upload_individual" in request.POST:
            print(request.POST)
            individual_form = IndividualReportUploadForm(request.POST, request.FILES)
            if individual_form.is_valid():
                reporte = individual_form.save()
                process_report(reporte.file.path, reporte)
                messages.success(request, f"Reporte subido y procesado correctamente.")
                return redirect("upload")

        elif "upload_zip" in request.POST:
            zip_form = ZipUploadForm(request.POST, request.FILES)
            if zip_form.is_valid():
                zip_file = zip_form.cleaned_data["zip_file"]
                company = zip_form.cleaned_data["company"]

                zip_dir = os.path.join(settings.MEDIA_ROOT, "zip_uploads")
                os.makedirs(zip_dir, exist_ok=True)
                zip_path = os.path.join(zip_dir, zip_file.name)

                with open(zip_path, "wb+") as destination:
                    for chunk in zip_file.chunks():
                        destination.write(chunk)

                process_zip(zip_path, company)

                messages.success(request, f"Archivo ZIP subido y procesado correctamente.")
                return redirect("upload")

    return render(
        request,
        "upload.html",
        {
            "individual_form": individual_form,
            "zip_form": zip_form,
            "companies": companies,
        },
    )


@login_required
def comparative_analysis_view(request):
    resultado = None

    def normalize_words(word_list):
        return set(
            w.strip().lower()
            for w in word_list
            if w
        )

    if request.method == "POST":
        form = ComparativeAnalysisForm(request.POST)
        print(form.errors)

        if form.is_valid():

            report = form.cleaned_data["report"]
            expert_list = form.cleaned_data["expert_list"]

            report_words = set(
                TotalCountReport.objects.filter(
                    report=report
                ).values_list(
                    "word",
                    flat=True
                )
            )

            expert_words = normalize_words(
                expert_list.words or []
            )

            resultado = {
                "report": report,
                "expert_list": expert_list,

                "comunes": sorted(
                    report_words & expert_words
                ),

                "solo_documento": sorted(
                    report_words - expert_words
                ),

                "solo_lista": sorted(
                    expert_words - report_words
                ),
            }

    else:
        form = ComparativeAnalysisForm()

    return render(
        request,
        "comparative_analysis.html",
        {
            "form": form,
            "resultado": resultado,
        }
    )

@login_required
def reports_by_year(request):

    year = request.GET.get("year")

    reports = (
        Report.objects
        .filter(year=year)
        .order_by("name")
    )

    data = [
        {
            "id": report.id,
            "name": report.name
        }
        for report in reports
    ]

    return JsonResponse(data, safe=False)

@login_required
@user_passes_test(lambda u: u.is_staff)
def user_view(request):
    users_qs = (
        User.objects.all()
        .select_related("profile")
        .order_by("username")
    )

    users = []
    for u in users_qs:
        expertise = getattr(u, "expert_profile", None)
        users.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_staff": u.is_staff,
            "is_active": u.is_active,
            "creation_date": u.profile.creation_date,
            "profession": expertise.profession if expertise else "",
        })

    return render(request, "users.html", {"users": users})


admin_required = user_passes_test(lambda u: u.is_staff)


def _admin_group():
    return Group.objects.get_or_create(name="Administrador")[0]


def _sync_admin_group(user, is_admin):
    if is_admin:
        user.groups.add(_admin_group())
    else:
        _admin_group().user_set.remove(user)


def _set_expert(user, profession):
    expertise, created = Expert.objects.get_or_create(
        user=user,
        defaults={"profession": profession},
    )
    if not created:
        expertise.profession = profession
        expertise.save()
    return expertise


@login_required
@admin_required
def create_user(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido."}, status=400)

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    is_admin = bool(data.get("is_staff"))
    is_active = bool(data.get("is_active", True))
    profession = (data.get("profession") or "").strip()

    if not username or not email or not password:
        return JsonResponse(
            {"success": False, "error": "Usuario, correo y contraseña son obligatorios."},
            status=400,
        )

    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse(
            {"success": False, "error": "Ese nombre de usuario ya está en uso."},
            status=400,
        )

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse(
            {"success": False, "error": "Ese correo ya está en uso."},
            status=400,
        )

    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=is_admin,
            is_active=is_active,
        )
    except IntegrityError:
        return JsonResponse({"success": False, "error": "No se pudo crear el usuario."}, status=400)

    if is_admin:
        _sync_admin_group(user, True)

    if profession:
        _set_expert(user, profession)

    return JsonResponse({"success": True, "id": user.id, "username": user.username})


@login_required
@admin_required
def update_user(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido."}, status=400)

    user_id = data.get("user_id")
    if not user_id:
        return JsonResponse({"success": False, "error": "Falta el id de usuario."}, status=400)

    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"success": False, "error": "Usuario no encontrado."}, status=404)

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()

    if username and not User.objects.filter(username__iexact=username).exclude(id=user.id).exists():
        user.username = username
    elif username:
        return JsonResponse(
            {"success": False, "error": "Ese nombre de usuario ya está en uso."},
            status=400,
        )

    if email and not User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
        user.email = email
    elif email:
        return JsonResponse(
            {"success": False, "error": "Ese correo ya está en uso."},
            status=400,
        )

    if "is_staff" in data:
        user.is_staff = bool(data["is_staff"])
        _sync_admin_group(user, user.is_staff)

    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    user.save()

    if "profession" in data:
        profession = (data.get("profession") or "").strip()
        if profession:
            _set_expert(user, profession)
        else:
            Expert.objects.filter(user=user).delete()

    return JsonResponse({"success": True})


@login_required
@admin_required
def toggle_user_active(request, user_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"success": False, "error": "Usuario no encontrado."}, status=404)

    if user.id == request.user.id:
        return JsonResponse(
            {"success": False, "error": "No puedes desactivar tu propia cuenta."},
            status=400,
        )

    user.is_active = not user.is_active
    user.save()

    return JsonResponse({"success": True, "is_active": user.is_active})


@login_required
@admin_required
def assign_expert(request, user_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"success": False, "error": "Usuario no encontrado."}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}

    profession = (data.get("profession") or "").strip()
    remove = bool(data.get("remove"))

    if remove or not profession:
        Expert.objects.filter(user=user).delete()
        return JsonResponse({"success": True, "expert": False})

    _set_expert(user, profession)
    return JsonResponse({"success": True, "expert": True})
