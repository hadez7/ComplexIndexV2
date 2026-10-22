import os
import json
import uuid
import shutil
import zipfile
import re
from django.core.files import File
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.conf import settings
from django.db import models, IntegrityError
from ..models import Company, TotalCountReport, Report, Workspace, WorkspaceMembership, TotalCount, ConcealmentReview
from ..forms import IndividualReportUploadForm, ZipUploadForm, ComparativeAnalysisForm
from ..main import process_report, process_zip
from ..workspace_utils import get_active_workspace, is_expert_user
from ..utils import calcular_complejidad_general
from User.models import Expert, PROFESSION_CHOICES

# * ---------------------------------------- VISTAS GENERALES ----------------------------------------
def index_view(request):
    return render(request, "index.html")


def get_recent_reports_data(current_ws, limit=5):
    """Retorna los expedientes más recientes del espacio con métricas calculadas."""
    recent_reports_qs = (
        Report.objects.filter(workspace=current_ws)
        .select_related('company')
        .order_by('-upload_date', '-id')[:limit]
    )
    recent_reports = []
    for rep in recent_reports_qs:
        comp_name = rep.company.name if rep.company else "Sin empresa"
        parts = comp_name.strip().split()
        if len(parts) >= 2:
            initials = f"{parts[0][0]}{parts[1][0]}".upper()
        elif parts and parts[0]:
            initials = parts[0][:2].upper()
        else:
            initials = "EX"

        rw = rep.total_words or 0
        ru = rep.unique_words or 0
        rt = rep.technical_words_count or 0
        rdiv = (ru / rw) if rw > 0 else 0.0
        rread = max(0.0, min(1.0, 1.0 - rep.inflesz_score)) if rep.inflesz_score is not None else 0.0
        rtech = (rt / rw) if rw > 0 else 0.0
        rc_score = calcular_complejidad_general(rdiv, rread, rtech)

        if rw == 0:
            status_text = "Pendiente"
            status_tone = "pending"
            progress_pct = 24
            detail_text = "En espera de reconocimiento OCR / extracción"
        elif rc_score > 0.62:
            status_text = "Revisión"
            status_tone = "alert"
            progress_pct = 100
            detail_text = f"Análisis lingüístico completado · {rw:,} palabras analizadas".replace(',', '.')
        else:
            status_text = "Validado"
            status_tone = "success"
            progress_pct = 100
            detail_text = f"Análisis lingüístico completado · {rw:,} palabras analizadas".replace(',', '.')

        recent_reports.append({
            'id': rep.id,
            'initials': initials,
            'company_name': comp_name,
            'report_name': rep.name or "Memoria de gestión",
            'year': rep.year or "-",
            'total_words': f"{rw:,}".replace(',', '.') if rw > 0 else "0",
            'complexity_index': f"{rc_score:.3f}",
            'status_text': status_text,
            'status_tone': status_tone,
            'progress_pct': progress_pct,
            'detail_text': detail_text,
        })
    return recent_reports


@login_required
def panel_view(request):
    current_ws = get_active_workspace(request)
    # Denegar por defecto: sin espacio activo, el filtro devuelve 0 filas (nunca "todo").
    total_companies = Company.objects.filter(workspace=current_ws).count()
    total_reports = Report.objects.filter(workspace=current_ws).count()

    # Agregación global del corpus en el espacio
    agg = Report.objects.filter(workspace=current_ws).aggregate(
        total_words=models.Sum('total_words'),
        total_unique=models.Sum('unique_words'),
        total_technical=models.Sum('technical_words_count'),
        avg_inflesz=models.Avg('inflesz_score'),
    )
    total_words_agg = agg['total_words'] or 0
    total_unique_agg = agg['total_unique'] or 0
    total_tech_agg = agg['total_technical'] or 0
    avg_inflesz_raw = agg['avg_inflesz']

    # Métricas del Signal Board
    if total_words_agg > 0:
        avg_diversity_pct = round((total_unique_agg / total_words_agg) * 100, 1)
        avg_tech_pct = round((total_tech_agg / total_words_agg) * 100, 1)
    else:
        avg_diversity_pct = 0.0
        avg_tech_pct = 0.0

    if avg_inflesz_raw is not None:
        avg_inflesz_display = f"{avg_inflesz_raw:.1f}" if avg_inflesz_raw > 1.0 else f"{avg_inflesz_raw:.3f}"
        if avg_inflesz_raw <= 0.4:
            inflesz_status = "Difícil"
            inflesz_tone = "warn"
        elif avg_inflesz_raw <= 0.6:
            inflesz_status = "Moderado"
            inflesz_tone = "warn"
        else:
            inflesz_status = "Legible"
            inflesz_tone = "good"
        readability_norm = max(0.0, min(1.0, 1.0 - avg_inflesz_raw))
    else:
        avg_inflesz_display = "--"
        inflesz_status = "Sin datos"
        inflesz_tone = "info"
        readability_norm = 0.0

    diversity_norm = (total_unique_agg / total_words_agg) if total_words_agg > 0 else 0.0
    tech_norm = (total_tech_agg / total_words_agg) if total_words_agg > 0 else 0.0
    global_complexity = calcular_complejidad_general(diversity_norm, readability_norm, tech_norm)
    avg_complexity_score = round(global_complexity * 100, 1) if total_reports > 0 else 0.0

    # Expedientes recientes para la tabla del observatorio
    recent_reports = get_recent_reports_data(current_ws, limit=5)

    # Señales prioritarias de opacidad / léxico
    opacity_signals = []
    reviews = ConcealmentReview.objects.filter(report__workspace=current_ws).order_by('-total_found')[:4]
    if reviews.exists():
        max_found = max(r.total_found for r in reviews) or 1
        for rev in reviews:
            lvl = min(100, max(20, int((rev.total_found / max_found) * 85)))
            opacity_signals.append({
                'term': rev.word,
                'count': f"{rev.total_found} detectados",
                'level': lvl
            })
    else:
        high_counts = TotalCount.objects.filter(workspace=current_ws).exclude(
            word__in=['de', 'la', 'el', 'y', 'en', 'a', 'los', 'del', 'las', 'por', 'un', 'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'se', 'que']
        ).order_by('-quantity')[:4]
        if high_counts.exists():
            max_q = max(h.quantity for h in high_counts) or 1
            for h in high_counts:
                lvl = min(100, max(25, int((h.quantity / max_q) * 88)))
                opacity_signals.append({
                    'term': h.word.capitalize(),
                    'count': f"{h.quantity:,}".replace(',', '.') + " apariciones",
                    'level': lvl
                })
        else:
            opacity_signals = [
                {'term': 'Salvo error u omisión', 'count': '18 apariciones', 'level': 78},
                {'term': 'A juicio de la administración', 'count': '14 apariciones', 'level': 62},
                {'term': 'Circunstancias imprevistas', 'count': '12 apariciones', 'level': 54},
                {'term': 'En la medida de lo posible', 'count': '10 apariciones', 'level': 41},
            ]

    # Barras de señal para el espectro de dispersión
    signal_bars = [28, 45, 38, 62, 51, 73, 58, 81, 66, 78, 70, 88, 74, 83]

    total_experts = Expert.objects.count()

    context = {
        'total_companies': total_companies,
        'total_reports': total_reports,
        'total_palabras': f'{total_words_agg:,}'.replace(',', '.'),
        'total_experts': total_experts,
        'current_workspace': current_ws,
        'avg_complexity_score': avg_complexity_score,
        'avg_diversity_pct': avg_diversity_pct,
        'avg_tech_pct': avg_tech_pct,
        'avg_inflesz_display': avg_inflesz_display,
        'inflesz_status': inflesz_status,
        'inflesz_tone': inflesz_tone,
        'recent_reports': recent_reports,
        'opacity_signals': opacity_signals,
        'signal_bars': signal_bars,
    }
    return render(request, 'panel.html', context)


@login_required
def upload_view(request):
    current_ws = get_active_workspace(request)
    individual_form = IndividualReportUploadForm(workspace=current_ws)
    zip_form = ZipUploadForm(workspace=current_ws)
    companies = Company.objects.filter(workspace=current_ws)

    if request.method == "POST":
        if "upload_individual" in request.POST:
            individual_form = IndividualReportUploadForm(request.POST, request.FILES, workspace=current_ws)
            if individual_form.is_valid():
                company = individual_form.cleaned_data.get("company")
                year = individual_form.cleaned_data.get("year")
                overwrite = individual_form.cleaned_data.get("overwrite")
                file = individual_form.cleaned_data.get("file")
                name = individual_form.cleaned_data.get("name") or file.name

                existing_report = None
                if company and year:
                    query = Report.objects.filter(
                        company=company, year=year, workspace=current_ws
                    )
                    existing_report = query.first()

                if existing_report and overwrite:
                    existing_report.name = name
                    existing_report.file = file
                    existing_report.save()
                    reporte = existing_report
                else:
                    reporte = individual_form.save(commit=False)
                    reporte.workspace = current_ws
                    reporte.save()

                res = process_report(reporte.file.path, reporte)
                if res.get("success"):
                    messages.success(
                        request,
                        f"Reporte '{reporte.name}' procesado con éxito: {res.get('total_words', 0):,} palabras analizadas."
                    )
                elif res.get("warning"):
                    messages.warning(request, f"Reporte guardado con observaciones: {res['warning']}")
                else:
                    messages.error(request, f"Error al procesar el reporte: {res.get('error', 'Error desconocido')}")

                return redirect("upload")

        elif "upload_zip" in request.POST:
            zip_form = ZipUploadForm(request.POST, request.FILES, workspace=current_ws)
            if zip_form.is_valid():
                zip_file = zip_form.cleaned_data["zip_file"]
                company = zip_form.cleaned_data["company"]
                overwrite = zip_form.cleaned_data.get("overwrite", False)

                zip_dir = os.path.join(settings.MEDIA_ROOT, "zip_uploads")
                os.makedirs(zip_dir, exist_ok=True)
                zip_path = os.path.join(zip_dir, zip_file.name)

                with open(zip_path, "wb+") as destination:
                    for chunk in zip_file.chunks():
                        destination.write(chunk)

                stats = process_zip(zip_path, company, overwrite=overwrite, workspace=current_ws)

                msg_parts = [f"Archivo ZIP procesado: {stats['processed']} reporte(s) importado(s) exitosamente."]
                if stats['skipped'] > 0:
                    msg_parts.append(f"{stats['skipped']} reporte(s) omitido(s) por ya existir.")
                if stats['errors']:
                    msg_parts.append(f"{len(stats['errors'])} archivo(s) con advertencias o errores.")
                    messages.warning(request, ' '.join(msg_parts))
                else:
                    messages.success(request, ' '.join(msg_parts))

                return redirect("upload")

    recent_reports = get_recent_reports_data(current_ws, limit=5)

    return render(
        request,
        "upload.html",
        {
            "individual_form": individual_form,
            "zip_form": zip_form,
            "companies": companies,
            "recent_reports": recent_reports,
        },
    )


@login_required
def prepare_zip_batch_view(request):
    """
    Recibe el archivo ZIP, lo descomprime en un directorio temporal de lote
    y retorna la lista de PDFs detectados para procesarlos uno a uno desde la interfaz.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    current_ws = get_active_workspace(request)
    form = ZipUploadForm(request.POST, request.FILES, workspace=current_ws)
    if not form.is_valid():
        error_msg = form.errors.as_text()
        return JsonResponse({"success": False, "error": error_msg}, status=400)

    zip_file = form.cleaned_data["zip_file"]
    company = form.cleaned_data.get("company")
    overwrite = form.cleaned_data.get("overwrite", False)

    batch_id = str(uuid.uuid4())
    base_batches_dir = os.path.join(settings.MEDIA_ROOT, "zip_batches")
    batch_dir = os.path.join(base_batches_dir, batch_id)
    os.makedirs(batch_dir, exist_ok=True)

    try:
        temp_zip_path = os.path.join(batch_dir, "archive.zip")
        with open(temp_zip_path, "wb") as f:
            for chunk in zip_file.chunks():
                f.write(chunk)

        with zipfile.ZipFile(temp_zip_path, "r") as z:
            z.extractall(batch_dir)

        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)

        pdf_files = []
        for root, _, files in os.walk(batch_dir):
            if "__MACOSX" in root:
                continue
            for fname in sorted(files):
                if fname.startswith(".") or fname.startswith("._") or not fname.lower().endswith(".pdf"):
                    continue
                full_p = os.path.join(root, fname)
                rel_p = os.path.relpath(full_p, batch_dir)
                pdf_files.append(rel_p)

        if not pdf_files:
            shutil.rmtree(batch_dir, ignore_errors=True)
            return JsonResponse({
                "success": False,
                "error": "El archivo ZIP no contiene documentos en formato PDF (.pdf) válidos."
            }, status=400)

        manifest = {
            "batch_id": batch_id,
            "workspace_id": current_ws.id if current_ws else None,
            "company_id": company.id if company else None,
            "overwrite": overwrite,
            "total_files": len(pdf_files),
            "files": pdf_files
        }
        with open(os.path.join(batch_dir, "manifest.json"), "w", encoding="utf-8") as mf:
            json.dump(manifest, mf)

        return JsonResponse({
            "success": True,
            "batch_id": batch_id,
            "total_files": len(pdf_files),
            "files": pdf_files,
            "company_name": company.name if company else None,
            "overwrite": overwrite
        })

    except Exception as e:
        shutil.rmtree(batch_dir, ignore_errors=True)
        return JsonResponse({"success": False, "error": f"Error al descomprimir el ZIP: {str(e)}"}, status=500)


@login_required
def process_zip_item_view(request):
    """
    Procesa un archivo PDF individual perteneciente al lote batch_id.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    batch_id = data.get("batch_id")
    file_rel_path = data.get("file_path")

    if not batch_id or not file_rel_path:
        return JsonResponse({"success": False, "error": "Faltan parámetros de lote o archivo"}, status=400)

    if not re.match(r"^[a-zA-Z0-9_\-]+$", batch_id):
        return JsonResponse({"success": False, "error": "Identificador de lote inválido"}, status=400)

    current_ws = get_active_workspace(request)
    base_batches_dir = os.path.join(settings.MEDIA_ROOT, "zip_batches")
    batch_dir = os.path.join(base_batches_dir, batch_id)
    manifest_path = os.path.join(batch_dir, "manifest.json")

    if not os.path.exists(manifest_path):
        return JsonResponse({"success": False, "error": "El lote no existe o ya ha expirado"}, status=404)

    with open(manifest_path, "r", encoding="utf-8") as mf:
        manifest = json.load(mf)

    target_abs_path = os.path.normpath(os.path.join(batch_dir, file_rel_path))
    if not target_abs_path.startswith(os.path.normpath(batch_dir)) or not os.path.isfile(target_abs_path):
        return JsonResponse({"success": False, "error": "Archivo no encontrado en el lote"}, status=404)

    company_id = manifest.get("company_id")
    overwrite = manifest.get("overwrite", False)
    company = Company.objects.filter(id=company_id, workspace=current_ws).first() if company_id else None
    filename = os.path.basename(file_rel_path)

    try:
        existing_report = None
        if company:
            existing_report = Report.objects.filter(workspace=current_ws, company=company, name=filename).first()
        else:
            existing_report = Report.objects.filter(workspace=current_ws, name=filename).first()

        if existing_report and not overwrite:
            return JsonResponse({
                "success": True,
                "skipped": True,
                "filename": filename,
                "message": "Omitido: ya existe un reporte con este nombre en el espacio de trabajo."
            })

        with open(target_abs_path, "rb") as f:
            django_file = File(f)
            if existing_report and overwrite:
                report = existing_report
                report.file.save(filename, django_file, save=False)
            else:
                report = Report(workspace=current_ws, company=company, name=filename)
                report.file.save(filename, django_file, save=False)
            report.save()

        res = process_report(report.file.path, report)

        if res.get("success"):
            return JsonResponse({
                "success": True,
                "skipped": False,
                "filename": filename,
                "report_id": report.id,
                "report_name": report.name,
                "company_name": report.company.name if report.company else "Detectada automáticamente",
                "year": report.year or "Sin año",
                "total_words": report.total_words or 0,
                "warning": res.get("warning")
            })
        elif res.get("warning"):
            return JsonResponse({
                "success": True,
                "skipped": False,
                "warning": res["warning"],
                "filename": filename,
                "report_id": report.id,
                "total_words": report.total_words or 0
            })
        else:
            return JsonResponse({
                "success": False,
                "filename": filename,
                "error": res.get("error", "Error durante el análisis del documento")
            })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "filename": filename,
            "error": str(e)
        })


@login_required
def finish_zip_batch_view(request):
    """
    Limpia los archivos temporales del lote una vez finalizado el procesamiento.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    batch_id = data.get("batch_id")
    if batch_id and re.match(r"^[a-zA-Z0-9_\-]+$", batch_id):
        base_batches_dir = os.path.join(settings.MEDIA_ROOT, "zip_batches")
        batch_dir = os.path.join(base_batches_dir, batch_id)
        if os.path.exists(batch_dir):
            shutil.rmtree(batch_dir, ignore_errors=True)

    return JsonResponse({"success": True})


@login_required
def comparative_analysis_view(request):
    current_ws = get_active_workspace(request)
    resultado = None

    def normalize_words(word_list):
        return set(
            w.strip().lower()
            for w in word_list
            if w
        )

    if request.method == "POST":
        form = ComparativeAnalysisForm(request.POST, workspace=current_ws)

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

            report_label = (
                report.company.name.strip()
                if report.company and report.company.name
                else (report.name or f"Reporte {report.id}")
            )
            if report.company and report.name and report.name != str(report.year) and report.name.lower() != "reporte":
                report_label = f"{report.company.name.strip()} - {report.name}"

            resultado = {
                "report": report,
                "report_label": report_label,
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
        form = ComparativeAnalysisForm(workspace=current_ws)

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
    if not year:
        return JsonResponse([], safe=False)

    current_ws = get_active_workspace(request)
    reports_qs = Report.objects.filter(year=year, workspace=current_ws)

    reports = (
        reports_qs
        .select_related("company")
        .order_by("company__name", "name")
    )

    data = []
    for report in reports:
        company_name = report.company.name.strip() if report.company and report.company.name else ""
        if company_name:
            label = company_name
            if report.name and report.name != str(report.year) and report.name.lower() != "reporte":
                label = f"{company_name} - {report.name}"
        else:
            label = report.name or f"Reporte {report.id}"

        data.append({
            "id": report.id,
            "name": label,
        })

    return JsonResponse(data, safe=False)

@login_required
@user_passes_test(lambda u: u.is_staff)
def user_view(request):
    from django.utils import timezone
    users_qs = (
        User.objects.all()
        .select_related("profile", "expert_profile")
        .prefetch_related("workspace_memberships__workspace")
        .order_by("-is_active", "username")
    )

    users = []
    for u in users_qs:
        expertise = getattr(u, "expert_profile", None)
        profile = getattr(u, "profile", None)
        is_deleted = getattr(profile, "is_deleted", False) if profile else False
        deleted_at = getattr(profile, "deleted_at", None) if profile else None

        # Determinar rol inequívoco del sistema
        if u.is_staff or u.is_superuser:
            role = "admin"
            role_display = "Administrador"
            profession = ""
        elif expertise:
            role = "expert"
            role_display = "Experto"
            profession = expertise.profession or ""
        else:
            role = "auditor"
            role_display = "Auditor"
            profession = ""

        # Espacios de trabajo asignados
        memberships = u.workspace_memberships.filter(workspace__is_archived=False)
        workspaces = [m.workspace.name for m in memberships]
        primary_workspace_id = memberships.first().workspace_id if memberships.exists() else None

        users.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
            "is_active": u.is_active,
            "is_deleted": is_deleted,
            "deleted_at": deleted_at,
            "last_login": u.last_login,
            "creation_date": profile.creation_date if profile else u.date_joined,
            "profession": profession,
            "role": role,
            "role_display": role_display,
            "workspaces": workspaces,
            "primary_workspace_id": primary_workspace_id,
        })

    total_users = len(users)
    active_users = sum(1 for u in users if u["is_active"] and not u["is_deleted"])
    deleted_users = sum(1 for u in users if u["is_deleted"])
    admin_users = sum(1 for u in users if u["role"] == "admin")
    expert_users = sum(1 for u in users if u["role"] == "expert")
    auditor_users = sum(1 for u in users if u["role"] == "auditor")

    return render(
        request,
        "users.html",
        {
            "users": users,
            "total_users": total_users,
            "active_users": active_users,
            "deleted_users": deleted_users,
            "admin_users": admin_users,
            "expert_users": expert_users,
            "auditor_users": auditor_users,
            "profession_choices": PROFESSION_CHOICES,
            "all_workspaces": Workspace.objects.filter(is_archived=False).order_by("name"),
        }
    )


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
    role = (data.get("role") or "").strip().lower()
    is_active = bool(data.get("is_active", True))
    profession = (data.get("profession") or "").strip()
    workspace_id = data.get("workspace_id")

    # Retrocompatibilidad si envían is_staff en lugar de role
    if not role:
        if bool(data.get("is_staff")):
            role = "admin"
        elif profession:
            role = "expert"
        else:
            role = "auditor"

    if not username or not email or not password:
        return JsonResponse(
            {"success": False, "error": "Usuario, correo y contraseña son obligatorios."},
            status=400,
        )

    if role == "expert" and not profession:
        return JsonResponse(
            {"success": False, "error": "Debes seleccionar una especialidad del catálogo para el rol de Experto."},
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

    is_staff = (role == "admin")

    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=is_staff,
            is_active=is_active,
        )
    except IntegrityError:
        return JsonResponse({"success": False, "error": "No se pudo crear el usuario."}, status=400)

    _sync_admin_group(user, is_staff)

    assigned_ws_name = None
    if role == "expert":
        _set_expert(user, profession)
    else:
        Expert.objects.filter(user=user).delete()

    if workspace_id:
        ws = Workspace.objects.filter(id=workspace_id, is_archived=False).first()
        if ws:
            role_in_ws = "admin" if role == "admin" else "editor"
            WorkspaceMembership.objects.get_or_create(
                workspace=ws,
                user=user,
                defaults={"role": role_in_ws}
            )
            assigned_ws_name = ws.name

    # Registrar en auditoría
    from User.utils import log_user_action
    desc_extra = f" con especialidad '{profession}'" if role == "expert" else ""
    ws_extra = f" y asignado al espacio '{assigned_ws_name}'" if assigned_ws_name else ""
    role_names = {"admin": "Administrador", "expert": "Experto", "auditor": "Auditor"}
    log_user_action(
        actor=request.user,
        target_username=user.username,
        target_user=user,
        action='CREATE',
        description=f"El administrador '{request.user.username}' creó la cuenta de '{user.username}' con rol '{role_names.get(role, role)}'{desc_extra}{ws_extra}.",
        details={
            "email": email,
            "role": role,
            "is_staff": is_staff,
            "is_active": is_active,
            "profession": profession if role == "expert" else None,
            "workspace": assigned_ws_name,
        },
        request=request
    )

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
    password = data.get("password")
    role = (data.get("role") or "").strip().lower()
    profession = (data.get("profession") or "").strip()
    workspace_id = data.get("workspace_id")

    changes = {}

    if username and username != user.username:
        if User.objects.filter(username__iexact=username).exclude(id=user.id).exists():
            return JsonResponse({"success": False, "error": "Ese nombre de usuario ya está en uso."}, status=400)
        changes["username"] = {"anterior": user.username, "nuevo": username}
        user.username = username

    if email and email != user.email:
        if User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
            return JsonResponse({"success": False, "error": "Ese correo ya está en uso."}, status=400)
        changes["email"] = {"anterior": user.email, "nuevo": email}
        user.email = email

    if password:
        user.set_password(password)
        changes["password"] = "Contraseña actualizada administrativamente"

    if "is_active" in data:
        new_active = bool(data["is_active"])
        if new_active != user.is_active:
            changes["is_active"] = {"anterior": user.is_active, "nuevo": new_active}
            user.is_active = new_active
            # Si se reactiva, restaurar de baja lógica
            if new_active and hasattr(user, "profile") and user.profile.is_deleted:
                user.profile.is_deleted = False
                user.profile.deleted_at = None
                user.profile.save()
                changes["is_deleted"] = {"anterior": True, "nuevo": False}

    # Procesar rol
    current_exp = getattr(user, "expert_profile", None)
    old_role = "admin" if user.is_staff else ("expert" if current_exp else "auditor")

    if role:
        if role == "admin":
            if not user.is_staff:
                user.is_staff = True
                _sync_admin_group(user, True)
                changes["role"] = {"anterior": old_role, "nuevo": "admin"}
            if current_exp:
                Expert.objects.filter(user=user).delete()
                changes["profession"] = {"anterior": current_exp.profession, "nuevo": None}
        elif role == "expert":
            if not profession:
                return JsonResponse({"success": False, "error": "Debes seleccionar una especialidad del catálogo para el rol de Experto."}, status=400)
            if user.is_staff:
                user.is_staff = False
                _sync_admin_group(user, False)
                changes["role"] = {"anterior": old_role, "nuevo": "expert"}
            old_prof = current_exp.profession if current_exp else ""
            if profession != old_prof:
                _set_expert(user, profession)
                changes["profession"] = {"anterior": old_prof, "nuevo": profession}
        elif role == "auditor":
            if user.is_staff:
                user.is_staff = False
                _sync_admin_group(user, False)
                changes["role"] = {"anterior": old_role, "nuevo": "auditor"}
            if current_exp:
                Expert.objects.filter(user=user).delete()
                changes["profession"] = {"anterior": current_exp.profession, "nuevo": None}
    else:
        # Retrocompatibilidad si mandaron is_staff
        if "is_staff" in data:
            new_staff = bool(data["is_staff"])
            if new_staff != user.is_staff:
                changes["is_staff"] = {"anterior": user.is_staff, "nuevo": new_staff}
                user.is_staff = new_staff
                _sync_admin_group(user, user.is_staff)
        if "profession" in data:
            old_prof = current_exp.profession if current_exp else ""
            if profession != old_prof:
                changes["profession"] = {"anterior": old_prof, "nuevo": profession}
                if profession:
                    _set_expert(user, profession)
                else:
                    Expert.objects.filter(user=user).delete()

    user.save()

    # Procesar asignación de espacio si fue provisto
    if workspace_id:
        ws = Workspace.objects.filter(id=workspace_id, is_archived=False).first()
        if ws:
            role_in_ws = "admin" if user.is_staff else "editor"
            _, created_mem = WorkspaceMembership.objects.get_or_create(
                workspace=ws,
                user=user,
                defaults={"role": role_in_ws}
            )
            if created_mem:
                changes["workspace_assigned"] = ws.name

    # Registrar en auditoría
    from User.utils import log_user_action
    action_type = 'ROLE_CHANGE' if 'role' in changes or 'is_staff' in changes else ('PASSWORD_CHANGE' if 'password' in changes and len(changes) == 1 else 'UPDATE')
    log_user_action(
        actor=request.user,
        target_username=user.username,
        target_user=user,
        action=action_type,
        description=f"El administrador '{request.user.username}' actualizó los datos de '{user.username}'.",
        details=changes,
        request=request
    )

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
    # Si se reactiva, limpiar el flag de baja lógica
    if user.is_active and hasattr(user, "profile") and user.profile.is_deleted:
        user.profile.is_deleted = False
        user.profile.deleted_at = None
        user.profile.save()

    user.save()

    from User.utils import log_user_action
    action_type = 'RESTORE' if user.is_active else 'TOGGLE_ACTIVE'
    desc = f"El administrador '{request.user.username}' reactivó la cuenta de '{user.username}'." if user.is_active else f"El administrador '{request.user.username}' desactivó temporalmente la cuenta de '{user.username}'."
    log_user_action(
        actor=request.user,
        target_username=user.username,
        target_user=user,
        action=action_type,
        description=desc,
        details={"is_active": user.is_active},
        request=request
    )

    is_deleted = getattr(user.profile, 'is_deleted', False) if hasattr(user, 'profile') else False
    return JsonResponse({"success": True, "is_active": user.is_active, "is_deleted": is_deleted})


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

    workspace_id = data.get("workspace_id")
    assigned_ws_name = None

    if remove or not profession:
        Expert.objects.filter(user=user).delete()
        res_expert = False
    else:
        _set_expert(user, profession)
        res_expert = True
        if workspace_id:
            ws = Workspace.objects.filter(id=workspace_id, is_archived=False).first()
            if ws:
                WorkspaceMembership.objects.get_or_create(
                    workspace=ws,
                    user=user,
                    defaults={"role": "editor"}
                )
                assigned_ws_name = ws.name

    from User.utils import log_user_action
    desc_extra = f" y lo vinculó al espacio '{assigned_ws_name}'" if assigned_ws_name else ""
    log_user_action(
        actor=request.user,
        target_username=user.username,
        target_user=user,
        action='EXPERT_CHANGE',
        description=f"El administrador '{request.user.username}' asignó la especialidad '{profession}' a '{user.username}'{desc_extra}." if res_expert else f"El administrador '{request.user.username}' retiró la especialidad de '{user.username}'.",
        details={"profession": profession if res_expert else None, "workspace": assigned_ws_name},
        request=request
    )

    return JsonResponse({"success": True, "expert": res_expert, "workspace": assigned_ws_name})


@login_required
@admin_required
def delete_user(request, user_id):
    """
    Baja lógica (Soft Delete):
    Desactiva al usuario y marca is_deleted=True sin eliminar registros de auditoría históricos.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"success": False, "error": "Usuario no encontrado."}, status=404)

    if user.id == request.user.id:
        return JsonResponse(
            {"success": False, "error": "No puedes dar de baja tu propia cuenta."},
            status=400,
        )

    if user.is_superuser:
        return JsonResponse(
            {"success": False, "error": "No puedes dar de baja a un superusuario del sistema."},
            status=400,
        )

    from django.utils import timezone
    user.is_active = False
    user.save()

    if hasattr(user, "profile"):
        user.profile.is_deleted = True
        user.profile.deleted_at = timezone.now()
        user.profile.save()

    # Registrar en auditoría
    from User.utils import log_user_action
    log_user_action(
        actor=request.user,
        target_username=user.username,
        target_user=user,
        action='SOFT_DELETE',
        description=f"El administrador '{request.user.username}' dio de baja lógica (Soft Delete) a '{user.username}'.",
        details={"is_active": False, "is_deleted": True},
        request=request
    )

    return JsonResponse({
        "success": True,
        "username": user.username,
        "soft_deleted": True,
        "message": f"El usuario '{user.username}' ha sido dado de baja lógica correctamente. Su cuenta ha sido desactivada y su historial de auditorías permanece protegido."
    })


@login_required
@admin_required
def user_audit_logs(request):
    """Devuelve el historial de auditoría de usuarios en formato JSON."""
    from User.models import UserAuditLog

    user_id = request.GET.get("user_id")
    action = request.GET.get("action")

    logs_qs = UserAuditLog.objects.select_related("actor", "target_user").all()

    if user_id:
        logs_qs = logs_qs.filter(target_user_id=user_id)
    if action:
        logs_qs = logs_qs.filter(action=action)

    logs_qs = logs_qs[:50]

    data = []
    for l in logs_qs:
        data.append({
            "id": l.id,
            "timestamp": l.timestamp.strftime("%d/%m/%Y %H:%M"),
            "actor": l.actor.username if l.actor else "Sistema",
            "target": l.target_username,
            "action": l.action,
            "action_display": l.get_action_display(),
            "description": l.description,
            "ip_address": l.ip_address or "N/D",
            "details": l.details,
        })

    return JsonResponse({"success": True, "logs": data})
