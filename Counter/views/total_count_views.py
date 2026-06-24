from itertools import chain
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg
from django.http import HttpResponse
from django.shortcuts import render
import openpyxl

from ..models import TotalCount, Company, ExpertWord, Expert, TotalCountReport, Report


from django.db.models import Sum

def get_filtered_total_counts(request):
    """
    Aplica filtros sobre los reportes (año, empresa, lista de experto) y devuelve un conteo agrupado por palabra.
    """
    queryset = TotalCountReport.objects.all()
    year = request.GET.get("selected_year")
    company_id = request.GET.get("company")
    selected_list_name = request.GET.get("selected_list")

    if year:
        queryset = queryset.filter(report__year=year)
    if company_id:
        queryset = queryset.filter(report__company__id=company_id)

    if selected_list_name:
        try:
            expert_word_obj = ExpertWord.objects.filter(name=selected_list_name).first()
            if expert_word_obj and expert_word_obj.words:
                expert_words = list(expert_word_obj.words)
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


def get_complexity_metrics(request):
    """
    Obtiene los reportes filtrados con sus métricas de complejidad calculadas.
    Retorna una lista de diccionarios con datos por reporte.
    
    Escala de valores: 0-1
    - 0: Bajo (documento simple)
    - 0.5: Medio (complejidad moderada)
    - 1: Alto (documento muy complejo)
    
    Fórmula de Complejidad General:
    Complejidad = (Diversidad Léxica + (1 - Legibilidad) + Densidad Técnica) / 3
    """
    from ..utils import calcular_complejidad_general
    
    queryset = Report.objects.all()
    year = request.GET.get("selected_year")
    company_id = request.GET.get("company")
    
    if year:
        queryset = queryset.filter(year=year)
    if company_id:
        queryset = queryset.filter(company__id=company_id)
    
    # Ordenar por año descendente y nombre
    queryset = queryset.order_by('-year', 'company__name', 'name')
    
    reports_data = []
    
    for report in queryset:
        # Calcular diversidad léxica (palabras únicas / total de palabras) - Escala 0-1
        diversity_index = 0
        if report.total_words and report.total_words > 0:
            diversity_index = round((report.unique_words / report.total_words), 3)
        
        # Calcular legibilidad (basada en longitud de oración) - Escala 0-1
        # Normalización: máximo esperado de palabras por oración = 10
        # Si avg_sentence_length <= 10, legibilidad alta (cercana a 1)
        # Si avg_sentence_length > 10, legibilidad baja (cercana a 0)
        readability_index = report.inflesz_score or 0
        
        # Calcular densidad técnica (palabras técnicas / total de palabras) - Escala 0-1
        technical_density = 0
        if report.total_words and report.total_words > 0:
            technical_density = round((report.technical_words_count / report.total_words), 3)
        
        # Calcular complejidad general usando fórmula compuesta
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
    total_counts = get_filtered_total_counts(request)

    years = Report.objects.values_list("year", flat=True).distinct().order_by("-year")
    companies = Company.objects.filter(report__isnull=False).distinct().order_by("name")
    expert_lists = ExpertWord.objects.all()

    selected_list_name = request.GET.get("selected_list")
    selected_year = request.GET.get("selected_year")
    selected_company_id = request.GET.get("company")

    total_quantity = sum(item["quantity"] for item in total_counts)
    count = len(total_counts)
    average = round(total_quantity / count, 2) if count > 0 else 0
    word_average = get_word_average(total_counts, average)
    
    # Obtener métricas de complejidad
    complexity_metrics = get_complexity_metrics(request)
    
    # Obtener información de empresa seleccionada (si aplica)
    selected_company = None
    if selected_company_id:
        selected_company = Company.objects.filter(id=selected_company_id).first()

    return render(request, "totalcount.html", {
        "total_counts": total_counts,
        "companies": companies,
        "average": average,
        "word_average": word_average,
        "expert_lists": expert_lists,
        "selected_list_name": selected_list_name,
        "years": years,
        "selected_year": selected_year,
        "selected_company": selected_company,
        "complexity_metrics": complexity_metrics,
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