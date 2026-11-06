"""
Módulo de Análisis de Co-Inercia (Co-Inertia Analysis - CIA) y Coeficiente RV de Escoufier.
Utilizado para el acoplamiento y contraste longitudinal de matrices documentales y léxicas.
"""

import math
import numpy as np
from django.db import models
from .models import Report, Company, TotalCountReport, ExpertWord


def compute_rv_coefficient(X, Y):
    """
    Calcula el Coeficiente RV de Escoufier entre dos matrices X (n x p) e Y (n x q)
    que comparten las mismas n observaciones (filas).
    
    Retorna:
        rv (float): Coeficiente de correlación multivariante entre [0.0, 1.0].
        distance (float): Distancia métrica euclidiana derivada d = sqrt(2 * (1 - RV)).
    """
    if X is None or Y is None or X.size == 0 or Y.size == 0:
        return 0.0, math.sqrt(2.0)

    n_x, p_x = X.shape
    n_y, p_y = Y.shape

    if n_x != n_y or n_x < 2:
        return 0.0, math.sqrt(2.0)

    # 1. Centrado por columnas (media cero)
    Xc = X - np.mean(X, axis=0)
    Yc = Y - np.mean(Y, axis=0)

    # 2. Operadores de covarianza / asociación de filas Wx = Xc @ Xc.T, Wy = Yc @ Yc.T
    Wx = Xc @ Xc.T
    Wy = Yc @ Yc.T

    # 3. Producto escalar de Hilbert-Schmidt y normas de Frobenius
    cov_xy = np.trace(Wx @ Wy)
    norm_x = np.sqrt(max(0.0, np.trace(Wx @ Wx)))
    norm_y = np.sqrt(max(0.0, np.trace(Wy @ Wy)))

    denom = norm_x * norm_y
    if denom <= 1e-12:
        return 0.0, math.sqrt(2.0)

    rv = float(cov_xy / denom)
    # Acotar a [0.0, 1.0] por pequeñas imprecisiones numéricas
    rv = max(0.0, min(1.0, rv))
    distance = float(math.sqrt(max(0.0, 2.0 * (1.0 - rv))))

    return rv, distance


def permutation_test_rv(X, Y, n_permutations=100, seed=42):
    """
    Prueba de hipótesis no paramétrica de Monte Carlo para Co-Inercia:
    H0: Las matrices X e Y son estadísticamente independientes.
    H1: Existe una co-estructura / co-inercia significativa entre X e Y.
    """
    obs_rv, _ = compute_rv_coefficient(X, Y)
    if obs_rv <= 0.0 or n_permutations < 10:
        return obs_rv, 1.0

    rng = np.random.default_rng(seed)
    n = X.shape[0]
    count_greater = 0

    for _ in range(n_permutations):
        perm_idx = rng.permutation(n)
        Y_perm = Y[perm_idx, :]
        perm_rv, _ = compute_rv_coefficient(X, Y_perm)
        if perm_rv >= obs_rv:
            count_greater += 1

    p_value = float((count_greater + 1) / (n_permutations + 1))
    return obs_rv, p_value


def build_term_matrix(workspace, year, company_ids, vocab_words):
    """
    Construye una matriz numpy (n_companies x n_words) para un año y conjunto de empresas dado.
    """
    n = len(company_ids)
    p = len(vocab_words)
    if n == 0 or p == 0:
        return np.zeros((n, p))

    comp_to_idx = {c_id: i for i, c_id in enumerate(company_ids)}
    word_to_idx = {w.lower(): j for j, w in enumerate(vocab_words)}

    matrix = np.zeros((n, p), dtype=np.float64)

    qs = (
        TotalCountReport.objects
        .filter(
            report__workspace=workspace,
            report__year=year,
            report__company_id__in=company_ids,
            word__in=list(word_to_idx.keys())
        )
        .values('report__company_id', 'word')
        .annotate(total_qty=models.Sum('quantity'))
    )

    for item in qs:
        c_id = item['report__company_id']
        w = item['word'].lower()
        if c_id in comp_to_idx and w in word_to_idx:
            matrix[comp_to_idx[c_id], word_to_idx[w]] += item['total_qty']

    return matrix


def run_longitudinal_coinertia_analysis(workspace, base_year, expert_list_id=None, top_k=80, n_permutations=100):
    """
    Ejecuta el pipeline completo de Co-Inercia:
    1. Construye Matriz General X_base y Matriz Experto Y_base en base_year.
    2. Calcula Co-inercia (RV) y prueba de hipótesis entre X_base e Y_base.
    3. Compara base_year contra cada año histórico disponible t != base_year.
    4. Genera la geometría matemática para el Diagrama Radial (Estrella de 360°).
    """
    # Años disponibles en el espacio de trabajo
    all_years = list(
        Report.objects.filter(workspace=workspace)
        .exclude(year=None)
        .values_list('year', flat=True)
        .distinct()
        .order_by('year')
    )

    if not all_years:
        return None

    if base_year not in all_years:
        base_year = all_years[-1]

    # Empresas activas en el año base
    base_companies = list(
        Report.objects.filter(workspace=workspace, year=base_year)
        .exclude(company_id=None)
        .values_list('company_id', flat=True)
        .distinct()
    )

    if not base_companies:
        return None

    # Top K palabras más frecuentes en el corpus general del año base
    top_general_words = list(
        TotalCountReport.objects.filter(report__workspace=workspace, report__year=base_year)
        .values('word')
        .annotate(tot=models.Sum('quantity'))
        .order_by('-tot')[:top_k]
        .values_list('word', flat=True)
    )

    # Vocabulario de la lista de expertos (si se seleccionó una)
    expert_words = []
    expert_list_obj = None
    if expert_list_id:
        try:
            expert_list_obj = ExpertWord.objects.get(id=expert_list_id, workspace=workspace)
            raw_words = expert_list_obj.words or []
            expert_words = [w.strip().lower() for w in raw_words if w and w.strip()]
        except ExpertWord.DoesNotExist:
            expert_words = []

    # Si no se seleccionó lista o está vacía, usar listas existentes o fallback
    if not expert_words:
        first_list = ExpertWord.objects.filter(workspace=workspace).first()
        if first_list and first_list.words:
            expert_list_obj = first_list
            expert_words = [w.strip().lower() for w in first_list.words if w and w.strip()]

    # 1. Matriz General X_base y Matriz Experta Y_base
    X_base = build_term_matrix(workspace, base_year, base_companies, top_general_words)
    has_expert_matrix = len(expert_words) > 0
    Y_base = build_term_matrix(workspace, base_year, base_companies, expert_words) if has_expert_matrix else None

    # 2. Co-Inercia General vs Experto en el Año Base (Test de Hipótesis)
    rv_coupling = 0.0
    p_value = 1.0
    if has_expert_matrix and Y_base is not None and Y_base.shape[1] > 0:
        rv_coupling, p_value = permutation_test_rv(X_base, Y_base, n_permutations=n_permutations)

    if p_value < 0.01:
        hypo_verdict = "Hipótesis Confirmada (p < 0.01)"
        hypo_tone = "success"
        hypo_desc = "Existe una correlación multivariante estadísticamente significativa entre el vocabulario corporativo y el marco normativo de expertos."
    elif p_value < 0.05:
        hypo_verdict = "Hipótesis Aceptada (p < 0.05)"
        hypo_tone = "info"
        hypo_desc = "Se detecta concordancia moderada entre el corpus y la lista de control del peritaje."
    else:
        hypo_verdict = "No Significativo (H0 no rechazada)"
        hypo_tone = "warn"
        hypo_desc = "No se observa una co-estructura lineal fuerte entre el vocabulario general y los términos de esta lista experta para este año."

    # 3. Comparación Temporal con los demás años (para el Radar / Gráfico de Estrella)
    # Años a contrastar (excluyendo o incluyendo base_year como referencia central/100%)
    comparison_years = [y for y in all_years if y != base_year]
    year_results = []

    for yr in comparison_years:
        yr_companies = set(
            Report.objects.filter(workspace=workspace, year=yr)
            .exclude(company_id=None)
            .values_list('company_id', flat=True)
        )
        # Empresas comunes para alinear las filas
        common = sorted(list(set(base_companies).intersection(yr_companies)))
        if len(common) < 3:
            continue

        X_base_sub = build_term_matrix(workspace, base_year, common, top_general_words)
        X_yr = build_term_matrix(workspace, yr, common, top_general_words)
        rv_gen, dist_gen = compute_rv_coefficient(X_base_sub, X_yr)

        rv_exp = 0.0
        dist_exp = math.sqrt(2.0)
        if has_expert_matrix:
            Y_base_sub = build_term_matrix(workspace, base_year, common, expert_words)
            Y_yr = build_term_matrix(workspace, yr, common, expert_words)
            rv_exp, dist_exp = compute_rv_coefficient(Y_base_sub, Y_yr)

        year_results.append({
            'year': yr,
            'common_companies': len(common),
            'rv_general': round(rv_gen, 4),
            'similarity_general_pct': round(rv_gen * 100, 1),
            'distance_general': round(dist_gen, 4),
            'rv_expert': round(rv_exp, 4),
            'similarity_expert_pct': round(rv_exp * 100, 1),
            'distance_expert': round(dist_exp, 4),
        })

    # Ordenar años cronológicamente
    year_results.sort(key=lambda x: x['year'])

    # 4. Geometría Matemática del Grafo en Estrella (Star Network Graph)
    # Centro del lienzo y dimensiones amplias con márgenes generosos
    cx, cy = 380, 380
    size = 760
    r_min = 105.0   # Radio mínimo (para distancias muy pequeñas / máxima afinidad)
    r_max = 245.0   # Radio máximo (deja > 110px de margen respecto a los bordes de 760)
    d_max = math.sqrt(2.0)  # ~1.4142

    center_node = {
        'year': base_year,
        'x': cx,
        'y': cy,
        'r': 34,
        'label': str(base_year),
    }

    # Órbitas de distancia métrica concéntricas (anillos guía del grafo)
    orbit_defs = [
        {'d': 0.35, 'label': 'd = 0.35 · Alta afinidad', 'tone': 'emerald'},
        {'d': 0.70, 'label': 'd = 0.70 · Concordancia', 'tone': 'blue'},
        {'d': 1.05, 'label': 'd = 1.05 · Distanciamiento', 'tone': 'amber'},
        {'d': 1.40, 'label': 'd = 1.40 · Máxima divergencia', 'tone': 'rose'},
    ]
    orbits = []
    for od in orbit_defs:
        r_orb = r_min + (od['d'] / d_max) * (r_max - r_min)
        orbits.append({
            'r': round(r_orb, 1),
            'label_y': round(cy - r_orb, 1),
            'd': od['d'],
            'label': od['label'],
            'tone': od['tone'],
        })

    n_axes = len(year_results)
    nodes_general = []
    nodes_expert = []
    star_spokes = []
    dual_pairs = []

    for i, item in enumerate(year_results):
        # Ángulo en radianes (iniciando en -90 grados / arriba)
        angle = -math.pi / 2 + (2 * math.pi * i / max(1, n_axes))
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Rayo guía de la estrella
        spoke_end_x = round(cx + (r_max + 18) * cos_a, 1)
        spoke_end_y = round(cy + (r_max + 18) * sin_a, 1)
        star_spokes.append({
            'year': item['year'],
            'x1': cx, 'y1': cy,
            'x2': spoke_end_x, 'y2': spoke_end_y,
            'lx': round(cx + (r_max + 36) * cos_a, 1),
            'ly': round(cy + (r_max + 36) * sin_a, 1),
        })

        # --- Vértice Matriz General ---
        d_gen = item['distance_general']
        u_gen = max(0.0, min(1.0, d_gen / d_max))
        r_gen = r_min + u_gen * (r_max - r_min)
        gx = round(cx + r_gen * cos_a, 1)
        gy = round(cy + r_gen * sin_a, 1)

        rv_gen = item['rv_general']
        if rv_gen >= 0.85:
            tone_gen = 'emerald'
            color_gen = '#10b981'
            desc_gen = 'Estructura léxica casi idéntica'
        elif rv_gen >= 0.65:
            tone_gen = 'blue'
            color_gen = '#3b82f6'
            desc_gen = 'Concordancia moderada-alta'
        elif rv_gen >= 0.40:
            tone_gen = 'amber'
            color_gen = '#f59e0b'
            desc_gen = 'Distanciamiento notable'
        else:
            tone_gen = 'rose'
            color_gen = '#ef4444'
            desc_gen = 'Fuerte divergencia estructural'

        node_g = {
            'year': item['year'],
            'x': gx,
            'y': gy,
            'r': 19,
            'distance': d_gen,
            'rv': rv_gen,
            'similarity_pct': item['similarity_general_pct'],
            'tone': tone_gen,
            'color': color_gen,
            'desc': desc_gen,
            'common_companies': item['common_companies'],
            'edge_x1': cx, 'edge_y1': cy,
            'edge_x2': gx, 'edge_y2': gy,
            'mid_x': round((cx + gx) / 2, 1),
            'mid_y': round((cy + gy) / 2, 1),
        }
        nodes_general.append(node_g)

        # --- Vértice Matriz de Expertos ---
        d_exp = item['distance_expert']
        u_exp = max(0.0, min(1.0, d_exp / d_max))
        r_exp = r_min + u_exp * (r_max - r_min)
        ex = round(cx + r_exp * cos_a, 1)
        ey = round(cy + r_exp * sin_a, 1)

        rv_exp = item['rv_expert']
        if rv_exp >= 0.85:
            tone_exp = 'emerald'
            color_exp = '#10b981'
            desc_exp = 'Alta afinidad con lista pericial'
        elif rv_exp >= 0.65:
            tone_exp = 'blue'
            color_exp = '#3b82f6'
            desc_exp = 'Concordancia pericial moderada'
        elif rv_exp >= 0.40:
            tone_exp = 'amber'
            color_exp = '#f59e0b'
            desc_exp = 'Distanciamiento de términos periciales'
        else:
            tone_exp = 'rose'
            color_exp = '#ef4444'
            desc_exp = 'Divergencia normativa severa'

        node_e = {
            'year': item['year'],
            'x': ex,
            'y': ey,
            'r': 19,
            'distance': d_exp,
            'rv': rv_exp,
            'similarity_pct': item['similarity_expert_pct'],
            'tone': tone_exp,
            'color': color_exp,
            'desc': desc_exp,
            'common_companies': item['common_companies'],
            'edge_x1': cx, 'edge_y1': cy,
            'edge_x2': ex, 'edge_y2': ey,
            'mid_x': round((cx + ex) / 2, 1),
            'mid_y': round((cy + ey) / 2, 1),
        }
        nodes_expert.append(node_e)

        # Conector para vista dual
        dual_pairs.append({
            'year': item['year'],
            'gx': gx, 'gy': gy,
            'ex': ex, 'ey': ey,
            'd_gen': d_gen,
            'd_exp': d_exp,
            'rv_gen': rv_gen,
            'rv_exp': rv_exp,
        })

    star_graph = {
        'cx': cx,
        'cy': cy,
        'size': size,
        'r_min': r_min,
        'r_max': r_max,
        'center_node': center_node,
        'orbits': orbits,
        'spokes': star_spokes,
        'nodes_general': nodes_general,
        'nodes_expert': nodes_expert,
        'dual_pairs': dual_pairs,
    }

    # Conservar radial_chart para retrocompatibilidad
    radial_chart = {
        'cx': cx,
        'cy': cy,
        'radius': r_max,
        'rings': [
            {'r': round(r_max * 0.2, 1), 'label': '20%'},
            {'r': round(r_max * 0.4, 1), 'label': '40%'},
            {'r': round(r_max * 0.6, 1), 'label': '60%'},
            {'r': round(r_max * 0.8, 1), 'label': '80%'},
            {'r': round(r_max * 1.0, 1), 'label': '100%'},
        ],
        'axes': star_spokes,
        'gen_polygon': "",
        'exp_polygon': "",
    }

    return {
        'base_year': base_year,
        'all_years': all_years,
        'expert_list': expert_list_obj,
        'total_companies_base': len(base_companies),
        'top_words_count': len(top_general_words),
        'expert_words_count': len(expert_words),
        'co_inertia': {
            'rv': round(rv_coupling, 4),
            'rv_pct': round(rv_coupling * 100, 1),
            'p_value': round(p_value, 4),
            'verdict': hypo_verdict,
            'tone': hypo_tone,
            'description': hypo_desc,
        },
        'star_graph': star_graph,
        'radial_chart': radial_chart,
        'comparison_table': year_results,
    }


def compare_company_across_years(workspace, company_id, year1, year2):
    """
    Compara el vocabulario y frecuencia de una misma empresa entre dos años distintos (Nivel Micro / Forense).
    """
    try:
        company = Company.objects.get(id=company_id, workspace=workspace)
    except Company.DoesNotExist:
        return None

    r1 = Report.objects.filter(workspace=workspace, company=company, year=year1).first()
    r2 = Report.objects.filter(workspace=workspace, company=company, year=year2).first()

    if not r1 or not r2:
        return {
            'company': company,
            'year1': year1,
            'year2': year2,
            'error': f"No se encontraron reportes registrados para {company.name} en ambos periodos seleccionados."
        }

    dict1 = dict(
        TotalCountReport.objects.filter(report=r1)
        .values_list('word', 'quantity')
    )
    dict2 = dict(
        TotalCountReport.objects.filter(report=r2)
        .values_list('word', 'quantity')
    )

    set1 = set(dict1.keys())
    set2 = set(dict2.keys())

    common_words = set1.intersection(set2)
    added_words = set2 - set1
    dropped_words = set1 - set2

    common_diffs = []
    for w in common_words:
        q1 = dict1[w]
        q2 = dict2[w]
        common_diffs.append({
            'word': w,
            'qty1': q1,
            'qty2': q2,
            'diff': q2 - q1,
            'ratio': round((q2 - q1) / max(1, q1) * 100, 1),
        })
    common_diffs.sort(key=lambda x: abs(x['diff']), reverse=True)

    added_list = [{'word': w, 'qty': dict2[w]} for w in added_words]
    added_list.sort(key=lambda x: x['qty'], reverse=True)

    dropped_list = [{'word': w, 'qty': dict1[w]} for w in dropped_words]
    dropped_list.sort(key=lambda x: x['qty'], reverse=True)

    # Coeficiente Jaccard de similitud léxica
    union_len = len(set1.union(set2))
    jaccard = round((len(common_words) / max(1, union_len)) * 100, 1)

    return {
        'company': company,
        'report1': r1,
        'report2': r2,
        'year1': year1,
        'year2': year2,
        'jaccard_similarity': jaccard,
        'common_count': len(common_words),
        'added_count': len(added_words),
        'dropped_count': len(dropped_words),
        'common_diffs': common_diffs[:50],
        'added_words': added_list[:50],
        'dropped_words': dropped_list[:50],
    }

