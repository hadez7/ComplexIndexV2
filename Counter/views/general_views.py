import os
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from ..models import Company
from ..forms import IndividualReportUploadForm, ZipUploadForm, ComparativeAnalysisForm
from ..main import process_report, process_zip
from ..models import TotalCountReport
from ..models import Report

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
def user_view(request):
    return render(request, "users.html")
