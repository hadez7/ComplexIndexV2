from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum, Avg
from django.db.models.functions import Trim
from itertools import chain
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import openpyxl

from ..models import TotalCount, Company, ExpertWord, Expert, TotalCountReport, Report
from ..workspace_utils import get_active_workspace


def get_filtered_total_counts(request):
    """
    Aplica filtros sobre los reportes (año, empresa, lista de experto) y devuelve un conteo agrupado por palabra.
    Aislado por el espacio de trabajo activo.
    """
    current_ws = get_active_workspace(request)
    # Denegar por defecto: sin espacio activo no hay nada que contar.
    queryset = TotalCountReport.objects.filter(report__workspace=current_ws)

    year = request.GET.get("selected_year")
    company_id = request.GET.get("company")
    selected_list_name = request.GET.get("selected_list")

    if year:
        queryset = queryset.filter(report__year=year)
    if company_id:
        queryset = queryset.filter(report__company__id=company_id)

    if selected_list_name:
        try:
            # La lista de palabras se busca además dentro del espacio activo:
            # no se cuestionan vocabularios de otros espacios.
            expert_word_obj = ExpertWord.objects.filter(
                workspace=current_ws, name=selected_list_name
            ).first()
            if expert_word_obj and expert_word_obj.words:
                expert_words = [str(w).strip().lower() for w in expert_word_obj.words if w]
                queryset = queryset.filter(word__in=expert_words)
            else:
                return []  # Lista vacía si no hay palabras
        except Expert.DoesNotExist:
            return []  # Usuario sin perfil de experto

    # Agrupar por palabra y sumar cantidad
    total_counts = (
        queryset
        .values("word")
        .annotate(quantity=Sum("quantity"))
        .order_by("-quantity")
    )

    return total_counts


def get_word_average(total_counts, average):
    return {
        item["word"]: round(item["quantity"] / average, 2) if item["quantity"] > 0 else 0
        for item in total_counts
    }


def get_complexity_metrics(request, offset=0, limit=None):
    """
    Obtiene los reportes filtrados con sus métricas de complejidad calculadas.
    Retorna una lista de diccionarios con datos por reporte dentro del espacio de trabajo activo.
    """
    from ..utils import calcular_complejidad_general
    
    current_ws = get_active_workspace(request)
    queryset = Report.objects.filter(workspace=current_ws).select_related('company')

    year = request.GET.get("selected_year")
    company_id = request.GET.get("company")
    
    if year:
        queryset = queryset.filter(year=year)
    if company_id:
        queryset = queryset.filter(company__id=company_id)
    
    # Ordenar por año descendente y nombre
    queryset = queryset.order_by('-year', 'company__name', 'name')
    if limit is not None:
        queryset = queryset[offset:offset + limit]

    reports_data = []
    
    for report in queryset:
        diversity_index = 0
        if report.total_words and report.total_words > 0:
            diversity_index = round((report.unique_words / report.total_words), 3)
        
        if report.inflesz_score is not None:
            readability_index = round(max(0.0, min(1.0, 1.0 - report.inflesz_score)), 3)
        else:
            readability_index = 0.0
        
        technical_density = 0
        if report.total_words and report.total_words > 0:
            technical_density = round((report.technical_words_count / report.total_words), 3)
        
        complexity_general = calcular_complejidad_general(
            diversity_index, 
            readability_index, 
            technical_density
        )
        
        reports_data.append({
            "ruc": report.company.ruc if report.company else "N/A",
            "company_name": report.company.name if report.company else "Sin empresa",
            "year": report.year or "N/A",
            "report_name": report.name,
            "total_words": report.total_words or 0,
            "unique_words": report.unique_words or 0,
            "total_sentences": report.total_sentences or 0,
            "avg_word_length": report.avg_word_length or 0,
            "avg_sentence_length": report.avg_sentence_length or 0,
            "technical_words": report.technical_words_count or 0,
            "complexity_general": complexity_general,
            "diversity_index": diversity_index,
            "readability_index": readability_index,
            "technical_density": technical_density,
        })
    
    return reports_data


@login_required
def total_count_view(request):
    current_ws = get_active_workspace(request)
    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.GET.get("ajax") == "1"
    )

    # -------------------------------------------------------------------------
    # 1. Endpoint AJAX de alta velocidad (JSON) para paginar y filtrar sin recargar
    # -------------------------------------------------------------------------
    if is_ajax:
        action = request.GET.get("action", "words")

        if action == "words":
            search_query = request.GET.get("search", "").strip().lower()
            rank_filter = request.GET.get("rank", "all")
            sort_col = request.GET.get("sort", "quantity")
            sort_dir = request.GET.get("dir", "desc")
            try:
                page_num = int(request.GET.get("page", 1) or 1)
            except (ValueError, TypeError):
                page_num = 1
            raw_page_size = request.GET.get("page_size", "25")

            queryset = get_filtered_total_counts(request)

            if isinstance(queryset, (list, tuple)):
                words_list = list(queryset)
            else:
                if search_query:
                    queryset = queryset.filter(word__icontains=search_query)
                if rank_filter == "min5":
                    queryset = queryset.filter(quantity__gte=5)

                order_prefix = "-" if sort_dir == "desc" else ""
                if sort_col == "word":
                    queryset = queryset.order_by(f"{order_prefix}word")
                else:
                    queryset = queryset.order_by(f"{order_prefix}quantity")

                if rank_filter == "top50":
                    queryset = queryset[:50]
                elif rank_filter == "top100":
                    queryset = queryset[:100]

                words_list = queryset

            total_items = len(words_list) if isinstance(words_list, (list, tuple)) else words_list.count()

            if raw_page_size == "all":
                page_size = min(total_items or 1, 500)
            else:
                try:
                    page_size = int(raw_page_size)
                except (ValueError, TypeError):
                    page_size = 25
            page_size = max(1, page_size)

            paginator = Paginator(words_list, page_size)
            page_obj = paginator.get_page(page_num)

            try:
                global_avg = float(request.GET.get("global_avg", 0) or 0)
            except (ValueError, TypeError):
                global_avg = 0

            if global_avg <= 0:
                base_calc_qs = TotalCountReport.objects.filter(report__workspace=current_ws)
                y = request.GET.get("selected_year")
                c = request.GET.get("company")
                if y:
                    base_calc_qs = base_calc_qs.filter(report__year=y)
                if c:
                    base_calc_qs = base_calc_qs.filter(report__company__id=c)
                agg = base_calc_qs.aggregate(total_q=Sum("quantity"), total_w=Count("word", distinct=True))
                tq = agg["total_q"] or 0
                tw = agg["total_w"] or 0
                global_avg = round(tq / tw, 2) if tw > 0 else 0

            words_data = [
                {
                    "word": item["word"],
                    "quantity": item["quantity"],
                    "weight": round(item["quantity"] / global_avg, 2) if global_avg > 0 else 0,
                }
                for item in page_obj
            ]

            return JsonResponse({
                "success": True,
                "total": total_items,
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "page_size": page_size,
                "average": global_avg,
                "words": words_data,
            })

        elif action == "complexity":
            search_query = request.GET.get("search", "").strip().lower()
            sort_col = request.GET.get("sort", "company")
            sort_dir = request.GET.get("dir", "asc")
            try:
                page_num = int(request.GET.get("page", 1) or 1)
            except (ValueError, TypeError):
                page_num = 1
            raw_page_size = request.GET.get("page_size", "25")

            metrics = get_complexity_metrics(request)

            if search_query:
                metrics = [
                    m for m in metrics
                    if search_query in str(m.get("ruc", "")).lower()
                    or search_query in str(m.get("company_name", "")).lower()
                    or search_query in str(m.get("report_name", "")).lower()
                    or search_query in str(m.get("year", "")).lower()
                ]

            reverse_sort = (sort_dir == "desc")
            if sort_col == "ruc":
                metrics.sort(key=lambda x: str(x.get("ruc", "")), reverse=reverse_sort)
            elif sort_col == "company":
                metrics.sort(key=lambda x: (str(x.get("company_name", "")).lower(), str(x.get("report_name", "")).lower()), reverse=reverse_sort)
            elif sort_col == "year":
                metrics.sort(key=lambda x: str(x.get("year", "")), reverse=reverse_sort)
            elif sort_col == "complexity":
                metrics.sort(key=lambda x: float(x.get("complexity_general", 0)), reverse=reverse_sort)
            elif sort_col == "diversity":
                metrics.sort(key=lambda x: float(x.get("diversity_index", 0)), reverse=reverse_sort)
            elif sort_col == "readability":
                metrics.sort(key=lambda x: float(x.get("readability_index", 0)), reverse=reverse_sort)
            elif sort_col == "density":
                metrics.sort(key=lambda x: float(x.get("technical_density", 0)), reverse=reverse_sort)

            total_items = len(metrics)
            if raw_page_size == "all":
                page_size = min(total_items or 1, 500)
            else:
                try:
                    page_size = int(raw_page_size)
                except (ValueError, TypeError):
                    page_size = 25
            page_size = max(1, page_size)

            paginator = Paginator(metrics, page_size)
            page_obj = paginator.get_page(page_num)

            return JsonResponse({
                "success": True,
                "total": total_items,
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "page_size": page_size,
                "reports": list(page_obj),
            })

    # -------------------------------------------------------------------------
    # 2. Renderizado Inicial de Página (HTML ultrarrápido con SSR paginado)
    # -------------------------------------------------------------------------
    total_counts_qs = get_filtered_total_counts(request)

    reports_qs = Report.objects.filter(workspace=current_ws)
    companies_qs = Company.objects.filter(workspace=current_ws)
    expert_lists = ExpertWord.objects.filter(workspace=current_ws)

    years = reports_qs.values_list("year", flat=True).distinct().order_by("-year")
    companies = companies_qs.filter(report__isnull=False).distinct().annotate(clean_name=Trim("name")).order_by("clean_name")

    selected_list_name = request.GET.get("selected_list")
    selected_year = request.GET.get("selected_year")
    selected_company_id = request.GET.get("company")

    # Cálculo ágil de totales para estadísticas
    if isinstance(total_counts_qs, (list, tuple)):
        total_quantity = sum(item["quantity"] for item in total_counts_qs)
        total_words_count = len(total_counts_qs)
    else:
        base_calc_qs = TotalCountReport.objects.filter(report__workspace=current_ws)
        if selected_year:
            base_calc_qs = base_calc_qs.filter(report__year=selected_year)
        if selected_company_id:
            base_calc_qs = base_calc_qs.filter(report__company__id=selected_company_id)
        if selected_list_name:
            expert_w = ExpertWord.objects.filter(workspace=current_ws, name=selected_list_name).first()
            if expert_w and expert_w.words:
                base_calc_qs = base_calc_qs.filter(word__in=list(expert_w.words))
            else:
                base_calc_qs = TotalCountReport.objects.none()

        agg = base_calc_qs.aggregate(total_q=Sum("quantity"), total_w=Count("word", distinct=True))
        total_quantity = agg["total_q"] or 0
        total_words_count = agg["total_w"] or 0

    average = round(total_quantity / total_words_count, 2) if total_words_count > 0 else 0

    # Paginación de palabras para la primera página
    words_paginator = Paginator(total_counts_qs, 25)
    words_page = words_paginator.get_page(1)
    word_average = get_word_average(words_page, average)

    # Métricas de complejidad optimizadas (primera página rápida)
    rep_count_qs = Report.objects.filter(workspace=current_ws)
    if selected_year:
        rep_count_qs = rep_count_qs.filter(year=selected_year)
    if selected_company_id:
        rep_count_qs = rep_count_qs.filter(company__id=selected_company_id)
    total_complexity_count = rep_count_qs.count()

    complexity_page = get_complexity_metrics(request, offset=0, limit=25)

    selected_company = None
    if selected_company_id:
        selected_company = Company.objects.filter(
            id=selected_company_id, workspace=current_ws
        ).first()

    return render(request, "totalcount.html", {
        "total_counts": words_page,
        "total_words_count": total_words_count,
        "companies": companies,
        "average": average,
        "word_average": word_average,
        "expert_lists": expert_lists,
        "selected_list_name": selected_list_name,
        "years": years,
        "selected_year": selected_year,
        "selected_company": selected_company,
        "complexity_metrics": complexity_page,
        "total_complexity_count": total_complexity_count,
    })



@login_required
def export_total_count_excel(request):
    total_counts = get_filtered_total_counts(request)  # ya devuelve valores agrupados
    total_quantity = sum(item["quantity"] for item in total_counts)
    count = len(total_counts)
    average = round(total_quantity / count, 2) if count > 0 else 0
    word_average = get_word_average(total_counts, average)

    # Crear Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Conteo Total"
    ws.append(["Palabra", "Cantidad", "Peso"])  # Solo columnas globales

    for item in total_counts:
        ws.append([
            item["word"],
            item["quantity"],
            word_average.get(item["word"], 0),
        ])

    ws.append([])
    ws.append(["", "Promedio total:", average])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=conteo_total.xlsx'
    wb.save(response)
    return response