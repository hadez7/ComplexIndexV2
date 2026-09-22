from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum
from django.http import JsonResponse
from ..models import (
    Report,
    ConcealmentReview,
    ConcealmentParagraphReview,
    TotalCountReport,
    TotalCount,
    ExpertWord,
)

from ..main import find_paragraph
from ..utils import quitar_tildes, recalcular_metricas_reporte


@login_required
def concealment_detection_view(request):

    reports = Report.objects.all()
    expert_lists = ExpertWord.objects.all()

    selected_report = None
    paragraphs = []

    palabra = ""
    report_id = None

    report_words = []

    origen_palabras = request.GET.get(
            "origen_palabras",
            "reporte"
        )

    lista_experto_id = request.GET.get(
            "lista_experto",
            ""
        )
    
    years = (
    Report.objects
    .values_list("year", flat=True)
    .distinct()
    .order_by("-year")
)

    if request.method == "POST":

        report_id = request.POST.get("report_id")
        palabra = request.POST.get("palabra")

        selected_report = get_object_or_404(
            Report,
            id=report_id
        )

        paragraphs = find_paragraph(
            selected_report,
            palabra
        )

        parrafos_validos = request.POST.getlist(
            "parrafos_validos"
        )

        total_found = sum(
            p["count"]
            for p in paragraphs
        )

        total_valid = 0

        review = ConcealmentReview.objects.create(
            report=selected_report,
            word=palabra,
            total_found=total_found,
            total_valid=0,
            total_discarded=0,
            reviewed_by=request.user
        )

        for indice, p in enumerate(paragraphs):

            es_valido = (
                str(indice)
                in parrafos_validos
            )

            ConcealmentParagraphReview.objects.create(
                review=review,
                paragraph_text=p["paragraph"],
                occurrences=p["count"],
                discarded=not es_valido
            )

            p["checked"] = es_valido

            if es_valido:
                total_valid += p["count"]

        review.total_valid = total_valid
        review.total_discarded = (
            total_found - total_valid
        )

        review.save()

        palabra_normalizada = quitar_tildes(
            palabra.lower().strip()
        )

        TotalCountReport.objects.update_or_create(
            report=selected_report,
            word=palabra_normalizada,
            defaults={
                "quantity": total_valid
            }
        )

        nuevo_total = (
            TotalCountReport.objects
            .filter(word=palabra_normalizada)
            .aggregate(total=Sum("quantity"))
        )["total"] or 0

        TotalCount.objects.update_or_create(
            word=palabra_normalizada,
            defaults={
                "quantity": nuevo_total
            }
        )

        recalcular_metricas_reporte(
            selected_report
        )

        report_words = (
            TotalCountReport.objects
            .filter(report=selected_report)
            .order_by("word")
            .values_list(
                "word",
                flat=True
            )
        )

    elif request.method == "GET":

        palabra = request.GET.get("palabra")
        report_id = request.GET.get("report_id")
        selected_year = request.GET.get("year")

        if selected_year:
            reports = Report.objects.filter(year=selected_year).order_by("name")
        else:
            reports = Report.objects.none()

        if report_id:

            selected_report = get_object_or_404(
                Report,
                id=report_id
            )

            report_words = (
                TotalCountReport.objects
                .filter(report=selected_report)
                .order_by("word")
                .values_list(
                    "word",
                    flat=True
                )
            )

        if palabra and report_id:

            paragraphs = find_paragraph(
                selected_report,
                palabra
            )

            ultima_revision = (
                ConcealmentReview.objects
                .filter(
                    report=selected_report,
                    word=palabra
                )
                .order_by("-reviewed_at")
                .first()
            )

            if ultima_revision:

                descartados = set(
                    ConcealmentParagraphReview.objects
                    .filter(
                        review=ultima_revision,
                        discarded=True
                    )
                    .values_list(
                        "paragraph_text",
                        flat=True
                    )
                )

                for p in paragraphs:
                    p["checked"] = (
                        p["paragraph"]
                        not in descartados
                    )

            else:

                for p in paragraphs:
                    p["checked"] = True

    if palabra is None:
        palabra = ""

    expert_lists_data = []

    for lista in expert_lists:

        expert_lists_data.append({
            "id": lista.id,
            "name": lista.name,
            "words": lista.words or []
        })

    return render(
        request,
        "concealment_detection.html",
        {
            "reports": reports,
            "expert_lists": expert_lists,
            "expert_lists_data": expert_lists_data,
            "report_words": report_words,
            "origen_palabras": origen_palabras,
            "lista_experto_id": lista_experto_id,

            "selected_report": selected_report,
            "paragraphs": paragraphs,
            "palabra": palabra,
            "years": years,
        },
    )

@login_required
def get_report_words(request):

    report_id = request.GET.get("report_id")

    if not report_id:
        return JsonResponse([], safe=False)

    palabras = list(
        TotalCountReport.objects
        .filter(report_id=report_id)
        .order_by("word")
        .values_list("word", flat=True)
    )

    return JsonResponse(palabras, safe=False)

@login_required
def get_reports_by_year(request):

    year = request.GET.get("year")

    reports = list(
        Report.objects
        .filter(year=year)
        .order_by("name")
        .values(
            "id",
            "name"
        )
    )

    return JsonResponse(
        reports,
        safe=False
    )