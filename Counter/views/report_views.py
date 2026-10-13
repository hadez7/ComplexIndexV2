from django.db.models.functions import Trim
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
import json
from ..models import Report, Company, TotalCountReport
from ..main import sincronizar_palabras_total_count
from ..workspace_utils import get_active_workspace


@login_required
def report_view(request):
    from django.db.models import Q
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    current_ws = get_active_workspace(request)
    query = request.GET.get("q", "").strip()
    order_by = request.GET.get("order_by", "year").strip()
    order_dir = request.GET.get("dir", "desc").strip()
    page_size_param = request.GET.get("page_size", "25").strip()

    # Queryset optimizado con select_related
    reports_qs = Report.objects.select_related("company").filter(workspace=current_ws)

    if query:
        reports_qs = reports_qs.filter(
            Q(company__name__icontains=query) | Q(year__icontains=query) | Q(name__icontains=query)
        )

    # Ordenamiento por columna solicitada
    if order_by == "company":
        sort_field = "-company__name" if order_dir == "desc" else "company__name"
    elif order_by == "year":
        sort_field = "-year" if order_dir == "desc" else "year"
    else:
        sort_field = "-year" if order_dir == "desc" else "year"

    reports_qs = reports_qs.order_by(sort_field, "-id")
    total_count = reports_qs.count()

    # Tamaño de página (10, 25, 50, 100)
    try:
        page_size = int(page_size_param)
        if page_size not in [10, 25, 50, 100]:
            page_size = 25
    except ValueError:
        page_size = 25

    paginator = Paginator(reports_qs, page_size)
    page_number = request.GET.get("page", 1)
    try:
        page_reports = paginator.get_page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_reports = paginator.get_page(1)

    companies = (
        Company.objects.filter(workspace=current_ws)
        .annotate(clean_name=Trim("name"))
        .order_by("clean_name")
    )

    return render(
        request,
        "reports.html",
        {
            "reports": page_reports,
            "total_reports_count": total_count,
            "companies": companies,
            "query": query,
            "current_workspace": current_ws,
            "order_by": order_by,
            "order_dir": order_dir,
            "page_size": page_size,
        },
    )


@login_required
def see_report_json(request, report_id):
    current_ws = get_active_workspace(request)
    try:
        report = Report.objects.select_related("company").get(
            id=report_id, workspace=current_ws
        )
        data = {
            "id": report.id,
            "name": report.name or "",
            "year": report.year or "",
            "company": {
                "id": report.company.id if report.company else None,
                "name": report.company.name if report.company else "Sin empresa asignada",
            },
            "upload_date": report.upload_date.strftime("%Y-%m-%d") if report.upload_date else "",
        }
        return JsonResponse(data)
    except Report.DoesNotExist:
        return JsonResponse({"error": "Reporte no encontrado"}, status=404)


@login_required
def delete_report(request, report_id):
    current_ws = get_active_workspace(request)
    try:
        report = Report.objects.get(id=report_id, workspace=current_ws)
        ws = report.workspace
        # Obtener palabras para descontarlas de TotalCount
        palabras_afectadas = list(
            TotalCountReport.objects.filter(report=report).values_list("word", flat=True)
        )
        report.delete()
        # Sincronizar TotalCount exacto para eliminar palabras fantasma en el workspace
        sincronizar_palabras_total_count(palabras_afectadas, workspace=ws)
        return HttpResponse(status=204)
    except Report.DoesNotExist:
        return HttpResponse(status=404)


@login_required
def update_report(request, report_id):
    current_ws = get_active_workspace(request)
    try:
        data = json.loads(request.body)
        report = Report.objects.get(id=report_id, workspace=current_ws)
        report.name = data.get("name", report.name)
        report.year = data.get("year", report.year)
        company_id = data.get("company")
        if company_id:
            report.company = Company.objects.get(id=company_id)
        else:
            report.company = None
        report.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
def check_report_duplicate_view(request):
    """
    Verifica si ya existe un reporte con la misma empresa y año
    en el espacio de trabajo actual para validación interactiva previa al envío.
    """
    current_ws = get_active_workspace(request)
    company_id = request.GET.get("company_id")
    year = request.GET.get("year")

    if not company_id or not year:
        return JsonResponse({"exists": False})

    try:
        report = Report.objects.filter(
            workspace=current_ws,
            company_id=company_id,
            year=year
        ).first()

        if report:
            return JsonResponse({
                "exists": True,
                "report_id": report.id,
                "report_name": report.name or "Sin nombre",
                "company_name": report.company.name if report.company else "",
                "year": report.year,
            })
        return JsonResponse({"exists": False})
    except Exception as e:
        return JsonResponse({"exists": False, "error": str(e)})

