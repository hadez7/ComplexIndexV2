from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from ..models import TotalCountReport, Report

@login_required
def total_count_report_view(request, report_id):
    results = list(
        TotalCountReport.objects.filter(report__id=report_id).order_by("-quantity")
    )
    report = Report.objects.get(id=report_id)
    conteos = TotalCountReport.objects.filter(report=report).order_by('-quantity')[:10]

    mid = len(results) // 2
    left = results[:mid]
    right = results[mid:]

    # Rellenar la lista más corta con None para igualar tamaños
    max_len = max(len(left), len(right))
    left += [None] * (max_len - len(left))
    right += [None] * (max_len - len(right))

    paired_results = list(zip(left, right))

    return render(
        request,
        "totalcountreport.html",
        {
            "paired_results": paired_results,
            "report": report,
            "top10_words": conteos,
        },
    )
