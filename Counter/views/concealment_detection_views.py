from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum
from django.db.models.functions import Trim
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
            Report.objects.select_related("company").annotate(clean_company=Trim("company__name")),
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
            user=request.user,
            word=palabra,
            total_found=total_found,
            total_valid=0,
            total_discarded=0
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

        selected_year = str(selected_report.year) if selected_report and selected_report.year else ""
        reports = (
            Report.objects
            .filter(year=selected_report.year)
            .select_related("company")
            .annotate(clean_company=Trim("company__name"))
            .order_by("clean_company", "name")
        )

    elif request.method == "GET":

        palabra = request.GET.get("palabra")
        report_id = request.GET.get("report_id")
        selected_year = request.GET.get("year") or ""

        if report_id:
            selected_report = get_object_or_404(
                Report.objects.select_related("company").annotate(clean_company=Trim("company__name")),
                id=report_id
            )
            if not selected_year and selected_report.year:
                selected_year = str(selected_report.year)

            report_words = (
                TotalCountReport.objects
                .filter(report=selected_report)
                .order_by("word")
                .values_list(
                    "word",
                    flat=True
                )
            )

        if selected_year:
            reports = (
                Report.objects
                .filter(year=selected_year)
                .select_related("company")
                .annotate(clean_company=Trim("company__name"))
                .order_by("clean_company", "name")
            )
        else:
            reports = Report.objects.none()

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

    recent_reviews = []
    if selected_report:
        recent_reviews = (
            ConcealmentReview.objects
            .filter(report=selected_report)
            .select_related("user")
            .order_by("-reviewed_at")[:5]
        )

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
            "selected_year": str(selected_year),
            "recent_reviews": recent_reviews,
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
    if not year:
        return JsonResponse([], safe=False)

    reports_qs = (
        Report.objects
        .filter(year=year)
        .select_related("company")
        .annotate(clean_company=Trim("company__name"))
        .order_by("clean_company", "name")
    )

    reports = []
    for r in reports_qs:
        company_name = getattr(r, "clean_company", None) or (r.company.name.strip() if r.company and r.company.name else "")
        if company_name:
            label = company_name
            if r.name and r.name != str(r.year) and r.name.lower() != "reporte":
                label = f"{company_name} - {r.name}"
        else:
            label = r.name or f"Reporte {r.id}"

        reports.append({
            "id": r.id,
            "name": label,
        })

    return JsonResponse(
        reports,
        safe=False
    )

@login_required
def concealment_history_view(request):
    reviews_qs = (
        ConcealmentReview.objects
        .select_related("report", "report__company", "user")
        .annotate(clean_company=Trim("report__company__name"))
        .order_by("-reviewed_at")
    )

    year_filter = request.GET.get("year", "").strip()
    company_filter = request.GET.get("company", "").strip()
    word_filter = request.GET.get("word", "").strip()
    user_filter = request.GET.get("user", "").strip()

    if year_filter:
        reviews_qs = reviews_qs.filter(report__year=year_filter)
    if company_filter:
        reviews_qs = reviews_qs.filter(report__company__name__icontains=company_filter)
    if word_filter:
        reviews_qs = reviews_qs.filter(word__icontains=word_filter)
    if user_filter:
        reviews_qs = reviews_qs.filter(user__username__icontains=user_filter)

    years = (
        Report.objects
        .values_list("year", flat=True)
        .distinct()
        .order_by("-year")
    )

    total_reviews_count = reviews_qs.count()
    total_words_validated = reviews_qs.aggregate(sum_valid=Sum("total_valid"))["sum_valid"] or 0
    total_words_discarded = reviews_qs.aggregate(sum_discarded=Sum("total_discarded"))["sum_discarded"] or 0

    return render(
        request,
        "concealment_history.html",
        {
            "reviews": reviews_qs[:100],
            "years": years,
            "year_filter": year_filter,
            "company_filter": company_filter,
            "word_filter": word_filter,
            "user_filter": user_filter,
            "total_reviews_count": total_reviews_count,
            "total_words_validated": total_words_validated,
            "total_words_discarded": total_words_discarded,
        },
    )


@login_required
def concealment_history_detail_ajax(request, review_id):
    review = get_object_or_404(
        ConcealmentReview.objects.select_related("report", "report__company", "user"),
        id=review_id
    )

    paragraphs = list(
        ConcealmentParagraphReview.objects
        .filter(review=review)
        .values("id", "paragraph_text", "occurrences", "discarded")
    )

    company_name = ""
    if review.report and review.report.company:
        company_name = review.report.company.name.strip()

    data = {
        "id": review.id,
        "word": review.word,
        "company": company_name,
        "year": review.report.year if review.report else None,
        "user": review.user.username if review.user else "Sin registrar",
        "reviewed_at": review.reviewed_at.strftime("%d/%m/%Y %H:%M"),
        "total_found": review.total_found,
        "total_valid": review.total_valid,
        "total_discarded": review.total_discarded,
        "paragraphs": paragraphs,
    }

    return JsonResponse(data)

