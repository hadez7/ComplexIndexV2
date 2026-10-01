from django.db.models.functions import Trim
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
import json
from ..models import Report, Company, TotalCountReport
from ..main import sincronizar_palabras_total_count
from ..workspace_utils import get_active_workspace


@login_required
def report_view(request):
    from django.db.models import Q

    current_ws = get_active_workspace(request)
    query = request.GET.get("q", "").strip()
    reports = Report.objects.select_related("company")
    if current_ws:
        reports = reports.filter(workspace=current_ws)

    if query:
        reports = reports.filter(
            Q(name__icontains=query) | Q(company__name__icontains=query)
        )

    companies_qs = Company.objects.all()
    if current_ws:
        companies_qs = companies_qs.filter(workspace=current_ws)
    companies = companies_qs.annotate(clean_name=Trim("name")).order_by("clean_name")

    return render(
        request,
        "reports.html",
        {
            "reports": reports,
            "companies": companies,
            "query": query,
            "current_workspace": current_ws,
        },
    )


def see_report_json(request, report_id):
    try:
        report = Report.objects.select_related("company").get(id=report_id)
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


def delete_report(request, report_id):
    try:
        report = Report.objects.get(id=report_id)
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


def update_report(request, report_id):
    try:
        data = json.loads(request.body)
        report = Report.objects.get(id=report_id)
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
