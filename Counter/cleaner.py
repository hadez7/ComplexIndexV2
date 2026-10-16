import os
import re
import unicodedata

try:
    from spellchecker import SpellChecker
    _spell = SpellChecker(language='es')
except Exception:
    _spell = None

# Tabla de sustitución de tildes y diacríticos que PRESERVA la 'ñ' y 'Ñ' intactas.
TABLA_QUITAR_TILDES = str.maketrans({
    'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
    'Á': 'a', 'É': 'e', 'Í': 'i', 'Ó': 'o', 'Ú': 'u',
    'ü': 'u', 'Ü': 'u',
    'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
    'À': 'a', 'È': 'e', 'Ì': 'i', 'Ò': 'o', 'Ù': 'u',
})


def quitar_tildes(texto: str) -> str:
    """Elimina tildes y diacríticos vocálicos preservando explícitamente la 'ñ' y 'Ñ'."""
    if not texto:
        return ""
    return texto.translate(TABLA_QUITAR_TILDES)


# Diccionario normalizado cargado en memoria para validaciones léxicas O(1)
_RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'resources')
_DICT_TXT = os.path.join(_RESOURCES_DIR, 'diccionario_es.txt')

if _spell:
    DICCIONARIO_ES_NORMALIZADO = {
        quitar_tildes(w.lower()): w
        for w in _spell.word_frequency.dictionary.keys()
    }
    if os.path.exists(_DICT_TXT):
        try:
            with open(_DICT_TXT, 'r', encoding='utf-8') as _f:
                for _line in _f:
                    _w = _line.strip().lower()
                    if _w:
                        DICCIONARIO_ES_NORMALIZADO[quitar_tildes(_w)] = _w
            _spell.word_frequency.load_text_file(_DICT_TXT)
        except Exception:
            pass
else:
    DICCIONARIO_ES_NORMALIZADO = {}


def _distancia_edicion_1(s1: str, s2: str) -> bool:
    """Retorna True si s1 y s2 tienen distancia Levenshtein exactamente igual a 1."""
    if abs(len(s1) - len(s2)) > 1:
        return False
    if len(s1) == len(s2):
        return sum(c1 != c2 for c1, c2 in zip(s1, s2)) == 1
    short, long_ = (s1, s2) if len(s1) < len(s2) else (s2, s1)
    for i in range(len(long_)):
        if long_[:i] + long_[i+1:] == short:
            return True
    return False


def en_diccionario_es(w: str) -> bool:
    """Valida si una palabra o su forma lematizada/singular/infinitivo pertenece al diccionario en español."""
    if not DICCIONARIO_ES_NORMALIZADO:
        return True  # Fallback si no está disponible la biblioteca
    w_low = w.lower()
    if w_low in DICCIONARIO_ES_NORMALIZADO:
        return True
    # Soporte para plurales regulares (-s, -es, -ces)
    if w_low.endswith('ces') and (w_low[:-3] + 'z') in DICCIONARIO_ES_NORMALIZADO:
        return True
    if w_low.endswith('es') and w_low[:-2] in DICCIONARIO_ES_NORMALIZADO:
        return True
    if w_low.endswith('s') and w_low[:-1] in DICCIONARIO_ES_NORMALIZADO:
        return True
    # Soporte para formas verbales regulares basadas en infinitivos (-ar, -er, -ir)
    if len(w_low) >= 4:
        for suffix, infinitivos in [
            ('ando', ['ar']), ('iendo', ['er', 'ir']),
            ('ado', ['ar']), ('ada', ['ar']), ('ados', ['ar']), ('adas', ['ar']),
            ('ido', ['er', 'ir']), ('ida', ['er', 'ir']), ('idos', ['er', 'ir']), ('idas', ['er', 'ir']),
            ('aron', ['ar']), ('ieron', ['er', 'ir']),
            ('aba', ['ar']), ('aban', ['ar']),
            ('amos', ['ar', 'er', 'ir']),
            ('an', ['ar']), ('en', ['er', 'ir']),
            ('as', ['ar']), ('es', ['er', 'ir']),
            ('o', ['ar', 'er', 'ir']), ('a', ['ar']), ('e', ['er', 'ir']),
        ]:
            if w_low.endswith(suffix):
                stem = w_low[:-len(suffix)]
                if len(stem) >= 2:
                    for inf in infinitivos:
                        if (stem + inf) in DICCIONARIO_ES_NORMALIZADO:
                            return True
    # Soporte para adverbios en -mente
    if w_low.endswith('mente') and len(w_low) > 6:
        base_adv = w_low[:-5]
        if base_adv in DICCIONARIO_ES_NORMALIZADO or (base_adv + 'o') in DICCIONARIO_ES_NORMALIZADO:
            return True
    # Soporte para sustantivos abstractos en -idad / -idades
    if w_low.endswith('idades') and len(w_low) > 7:
        w_low_sg = w_low[:-2]
    else:
        w_low_sg = w_low
    if w_low_sg.endswith('idad') and len(w_low_sg) > 5:
        stem_id = w_low_sg[:-4]
        if (
            stem_id in DICCIONARIO_ES_NORMALIZADO
            or (stem_id + 'al') in DICCIONARIO_ES_NORMALIZADO
            or (stem_id + 'o') in DICCIONARIO_ES_NORMALIZADO
            or (stem_id[:-2] + 'able') in DICCIONARIO_ES_NORMALIZADO
            or (stem_id[:-2] + 'ible') in DICCIONARIO_ES_NORMALIZADO
        ):
            return True
    return False


# Regex para números romanos (i, ii, iii, iv, v, vi, vii, viii, ix, x, xi, xii, etc.)
ROMAN_REGEX = re.compile(
    r'^(?:m{0,4}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3}))$',
    re.IGNORECASE
)

# Raíces semánticas frecuentes en español que empiezan por 'h' y pueden perderla en OCR
RAICES_H_VALIDAS = (
    'habit', 'habil', 'haciend', 'honor', 'hospit', 'haber', 'habid',
    'huelg', 'hipotec', 'hered', 'herenc', 'herram', 'hold', 'higien',
    'hallaz', 'homolog', 'horari', 'humani', 'hecho', 'hiel', 'hierr'
)

# Grupos consonánticos de 3 y 4 letras válidos en español y términos contables/corporativos
CONSONANTES_VALIDAS = {
    # 4 consonantes legítimas en español
    'nstr', 'nscr', 'rstr', 'bstr', 'dstr', 'pstr',
    # 3 consonantes legítimas en español (incluye grupos de s, n, r, l, z, x y dígrafos)
    'str', 'scr', 'ntr', 'ndr', 'mpr', 'mpl', 'ncl', 'rtr', 'rdr', 'mbr',
    'nfr', 'nfl', 'nst', 'nsc', 'rst', 'rsc', 'btr', 'ctr', 'xpr', 'xtr',
    'xcl', 'xpl', 'nsg', 'nsp', 'nsm', 'rch', 'nch', 'lch', 'rbr', 'rpr',
    'rgr', 'rcr', 'rfr', 'ldr', 'ltr', 'lbr', 'lpr', 'lcr', 'lgr', 'lfr',
    'bsp', 'dst', 'mbl', 'gth', 'sch', 'ght', 'lsh', 'rth', 'cth', 'kth',
    'zcl', 'spr', 'spl', 'sbr', 'sbl', 'sfr', 'sfl', 'scl', 'sgr', 'sgl',
    'ncr', 'ngr', 'ngl', 'rpl', 'rbl', 'rgl', 'lpl', 'lbl', 'lgl', 'squ',
    'nqu', 'lqu', 'rqu', 'dqu', 'bst', 'rsp', 'nsf', 'rsm', 'nsb', 'ccl',
    'bcl', 'nsv', 'nsd', 'nsl'
}

# Grupos consonánticos de 4 letras para retrocompatibilidad
CONSONANTES_VALIDAS_4 = {'nstr', 'nscr', 'rstr', 'bstr', 'dstr', 'pstr', 'ntr', 'ndr', 'mpr', 'mpl'}

# Consonantes que pueden duplicarse legítimamente en español
CONSONANTES_DOBLES_VALIDAS = {'c', 'r', 'l', 'n'}

# Letras que se pueden doblar legítimamente en palabras del español (ej: acción, leer, coordinar, perro, llave, innovar)
LETRAS_DOBLES_VALIDAS = {'c', 'e', 'o', 'r', 'l', 'n'}

# Palabras legítimas del español o extranjeras que terminan en 'del'
PALABRAS_GENUINAS_DEL = {
    'redondel', 'cordel', 'bedel', 'burdel', 'fidel', 'claudel', 'model', 
    'edel', 'andel', 'rondel', 'candela', 'mendel', 'haendel'
}

# Acrónimos y entidades corporativas legítimas comunes en el ecosistema financiero
ACRONIMOS_VALIDOS = {
    'bvq', 'bvg', 'scvs', 'biess', 'sri', 'iess', 'pwc', 'deloitte',
    'kpmg', 'ey', 'bce', 'cfn', 'niff', 'nic', 'supercias', 'iva', 'ir',
    'ruc', 'usd', 'pib', 'ebitda', 'cfo', 'ceo', 'sa', 'cia', 'ltda',
    'pichincha', 'guayas', 'azuay', 'manabi', 'loja', 'eloro', 'tungurahua',
    'chimborazo', 'imbabura', 'cotopaxi', 'esmeraldas', 'canar', 'carchi',
    'sucumbios', 'napo', 'pastaza', 'morona', 'zamora', 'galapagos', 'orellana',
    'santodomingo', 'santaelena', 'holcim', 'sabmiller', 'cepsa', 'pronaca',
    'supermaxi', 'dichem', 'armacar', 'holding', 'holdings', 'compliance',
    'leasing', 'factoring', 'joint', 'venture', 'cash', 'flow', 'hedge',
    'hedging', 'spread', 'swaps', 'broker', 'trust', 'offshore', 'online',
    'software', 'hardware', 'marketing', 'stock', 'management', 'retail',
    'covid', 'covid19', 'senores', 'compania', 'companias'
}

# Diccionario de sustituciones directas para artefactos de OCR recurrentes conocidos
ARTEFACTOS_RECURRENTES = {
    'aacccciio': 'accion',
    'accio': 'accion',
    'compaiiia': 'compañia',
    'compaia': 'compañia',
    'niisstaass': 'accionistas',
    'represenlanle': 'representante',
    'admlnlstraclon': 'administracion',
    'admnstracon': 'administracion',
    'socius': 'socios',
    'accoislas': 'accionistas',
    'accoiislas': 'accionistas',
    'ejereieio': 'ejercicio',
    'ejereicio': 'ejercicio',
    'audilorla': 'auditoria',
    'balanee': 'balance',
    'estadas': 'estados',
}


def limpiar_texto_estructural(texto: str) -> str:
    """
    Limpieza a nivel de documento antes de la tokenización:
    1. Normaliza ligaduras tipográficas (ﬁ -> fi, ﬂ -> fl).
    2. Elimina líneas de paginación intercaladas y reúne palabras partidas por guión de fin de línea.
    3. Separa números pegados a letras (19abril -> 19 abril, abril2024 -> abril 2024).
    4. Elimina apóstrofes o comillas dentro de palabras (ej. h'abitaciones -> habitaciones, d'e -> de).
    5. Sustituye caracteres de exclamación o barra vertical en medio de letras por 'i'.
    6. Convierte comillas («, », “, ”), aperturas (¿, ¡) y guiones largos (—) en delimitadores limpios.
    """
    if not texto:
        return ""

    # Normalización de ligaduras tipográficas
    texto = texto.replace('ﬁ', 'fi').replace('ﬂ', 'fl').replace('ﬀ', 'ff').replace('ﬃ', 'ffi').replace('ﬄ', 'ffl')

    # Eliminar líneas huérfanas de números de página o separadores de página intercalados
    texto = re.sub(r'\n\s*[-—_=]*\s*p[aá]gina\s+\d+(?:\s+de\s+\d+)?\s*[-—_=]*\s*\n', '\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\n\s*[-—_=]{3,}\s*\n', '\n', texto)
    texto = re.sub(r'\n\s*\d+\s*\n', '\n', texto)

    # 1. Reunir palabras partidas por guión de fin de línea (incluso a través de saltos de línea múltiples)
    texto = re.sub(r'([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{2,})-\s*\n+\s*([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{2,})', r'\1\2', texto)

    # 2. Despegar números y letras pegadas (ej. 19de abrildel 2024 -> 19 de abrildel 2024)
    texto = re.sub(r'(\d+)([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)', r'\1 \2', texto)
    texto = re.sub(r'([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)(\d+)', r'\1 \2', texto)

    # 3. Eliminar apóstrofes o comillas dentro de palabras (ej. h'abitaciones -> habitaciones, d'e -> de)
    texto = re.sub(r"(?<=[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ])['`´’‘](?=[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ])", "", texto)

    # 4. Sustituir caracteres de exclamación o barra vertical en medio de letras por 'i'
    texto = re.sub(r'(?<=[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ])[¡!|](?=[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ])', 'i', texto)

    # 5. Normalizar signos españoles de puntuación y comillas para garantizar límites seguros
    texto = re.sub(r'[«»“”"¿¡—–]', ' ', texto)

    return texto


def corregir_caracteres_repetidos(word: str) -> str:
    """
    Corrige anomalías de Faux-Bold y letras triplicadas:
    - Reduce 3 o más letras iguales a 2 (para c,e,o,r,l,n) o 1 (para las demás como a,i,u,b,d,etc.).
    """
    def _reducir_triple(m):
        ch = m.group(1)
        if ch in LETRAS_DOBLES_VALIDAS:
            return ch * 2
        return ch

    return re.sub(r'(.)\1{2,}', _reducir_triple, word)


def despegar_sufijo_preposicion(word: str) -> list[str]:
    """
    Despega la preposición 'del' unida accidentalmente al final de una palabra raíz:
    Ej: abrildel -> abril + del
        empresasdel -> empresas + del
        aplicaciondel -> aplicacion + del
    Preserva palabras reales del español como 'redondel', 'cordel', 'model'.
    """
    if word.endswith('del') and len(word) >= 7 and word not in PALABRAS_GENUINAS_DEL:
        raiz = word[:-3]
        if raiz.endswith(('s', 'l', 'n', 'cion', 'sion', 'dad', 'da')):
            return [raiz, 'del']
    return [word]


def es_palabra_valida_espanol(word: str, stopwords_normalizadas: set) -> bool:
    """
    Criterios fonotácticos y léxicos estrictos:
    1. Longitud entre 3 y 24 caracteres.
    2. Admite acrónimos y entidades corporativas válidas (bvq, bvg, scvs, deloitte, biess).
    3. No debe ser número romano (iii, viii, xxxiv, etc.).
    4. Debe contener al menos una vocal o 'y'.
    5. No debe consistir en el mismo carácter repetido (ej: aaa, zzz).
    6. No debe contener caracteres repetidos 3 o más veces consecutivas (ej. aaa, bbb).
    7. No debe tener 4 o más vocales consecutivas (incompatible con fonotáctica española).
    8. No debe tener 3 vocales abiertas consecutivas (ej: aeo, eoa, oae).
    9. No debe tener consonantes duplicadas inválidas en español (solo c, r, l, n son válidas).
    10. 'q' siempre debe ir acompañada de 'u[aeio]'.
    11. Combinaciones iniciales imposibles en español (ql, qv, xd, zz, etc.).
    12. Secuencias de 3 o más consonantes deben pertenecer a grupos válidos.
    13. Palabras que no pertenecen al diccionario no deben terminar en consonantes incompatibles con el español (b, f, g, j, k, p, v, w).
    14. No debe ser stopword normalizada.
    """
    longitud = len(word)
    if longitud < 3 or longitud > 24:
        return False

    # Acrónimos y entidades permitidas directamente
    if word in ACRONIMOS_VALIDOS:
        return True

    # Descartar números romanos
    if ROMAN_REGEX.match(word):
        return False

    # Debe contener al menos una vocal o 'y'
    if not re.search(r'[aeiouyáéíóúüñ]', word):
        return False

    # Descartar si el mismo carácter forma toda la palabra
    if len(set(word)) == 1:
        return False

    # Descartar 3 o más caracteres repetidos consecutivos (ej: aaa, bbb)
    if re.search(r'(.)\1{2,}', word):
        return False

    # Descartar secuencias imposibles de 4 o más vocales consecutivas
    if re.search(r'[aeiouáéíóúü]{4,}', word):
        return False

    # Descartar 3 vocales abiertas consecutivas (a, e, o)
    if re.search(r'[aeoáéó]{3,}', word):
        return False

    # Descartar consonantes duplicadas inválidas en español (solo c, r, l, n son legítimas)
    for m in re.finditer(r'([^aeiouyáéíóúüñ])\1', word):
        if m.group(1) not in CONSONANTES_DOBLES_VALIDAS:
            return False

    # Regla del español: 'q' siempre debe ir seguida de 'u'
    if 'q' in word and not re.search(r'qu[aeio]', word):
        return False

    # Combinaciones iniciales imposibles en español
    if re.match(r'^(ql|qv|qr|qp|qk|xd|zz|vv|jj|ww|bb|cc|dd|ff|gg|mm|pp|tt|aab|aae|eea|ooe)', word):
        return False

    # Descartar secuencias de 3 o más consonantes consecutivas si no pertenecen a grupos válidos
    # (se omiten palabras ya confirmadas en el léxico español)
    if not en_diccionario_es(word):
        consonantes_consecutivas = re.findall(r'[^aeiouyáéíóúüñ\s]{3,}', word)
        for grupo in consonantes_consecutivas:
            if len(grupo) > 4 or grupo not in CONSONANTES_VALIDAS:
                return False

    # Palabras cortas (longitud <= 3) no reconocidas en diccionario ni en acrónimos
    if longitud <= 3 and not en_diccionario_es(word) and word not in ACRONIMOS_VALIDOS:
        return False

    # Descartar palabras no reconocidas en diccionario que terminen en consonantes no permitidas en español
    if word[-1] in {'b', 'c', 'f', 'g', 'j', 'k', 'p', 'v', 'w', 'q'} and not en_diccionario_es(word):
        return False

    # 1. Reglas fonotácticas estrictas de la 'ñ':
    # La 'ñ' NUNCA puede ir seguida de una consonante en español (ej: ñs, ñp, ñn, ñt, etc.)
    if re.search(r'ñ[bcdfghjklmnñpqrstvwxyz]', word):
        return False

    # En lenguaje corporativo/financiero, palabras que inician por 'ñ' son 100% ruido OCR
    if word.startswith('ñ') and word not in {'ñandú', 'ñame'}:
        return False

    # 2. Reglas para doble 'a' inicial:
    # No puede iniciar con doble 'a' seguida de consonante (aam-, aañ-, aad-), salvo aar- (Aarón)
    if re.match(r'^aa[^r\s]', word):
        return False

    # 3. Descartar secuencias de 3 o más consonantes consecutivas si no pertenecen a grupos válidos
    # (se cuenta la 'ñ' como consonante)
    if not en_diccionario_es(word):
        consonantes_consecutivas = re.findall(r'[^aeiouyáéíóúü\s]{3,}', word)
        for grupo in consonantes_consecutivas:
            if len(grupo) > 4 or grupo not in CONSONANTES_VALIDAS:
                return False

    # 4. Puerta léxica estricta (Lista Blanca):
    # Si la palabra no existe en el lexicón enriquecido ni en acrónimos/entidades corporativas, se rechaza
    if not en_diccionario_es(word) and word not in ACRONIMOS_VALIDOS:
        return False

    # Descartar stopwords
    if word in stopwords_normalizadas:
        return False

    return True


def procesar_palabra_individual(token: str, stopwords_normalizadas: set) -> list[str]:
    """
    Normaliza, sanea y valida un token individual extraído del texto o de la base de datos.
    Aplica corrección heurística de OCR para recuperación de 'h' inicial caída (ej: abitacion -> habitacion),
    colapso de 'aa' inicial espurio (ej: aaño -> año), separación de compuestas pegadas
    y corrección Levenshtein de distancia 1 para erratas de escaneo.
    Devuelve una lista de 0, 1 o más palabras válidas resultantes.
    """
    norm = quitar_tildes(token.lower().strip())
    if len(norm) < 3:
        return []

    # 0. Colapsar 'aa' inicial defectuoso por Faux-Bold o arrastre de escáner (ej: aaño -> año, aapectos -> aspectos)
    if re.match(r'^aa[^r\s]', norm):
        sin_doble_a = norm[1:]
        if en_diccionario_es(sin_doble_a) or sin_doble_a in ACRONIMOS_VALIDOS:
            norm = sin_doble_a
        else:
            return []

    # 1. Reemplazo directo de artefactos recurrentes documentados
    if norm in ARTEFACTOS_RECURRENTES:
        norm = ARTEFACTOS_RECURRENTES[norm]

    # 2. Heurística segura de recuperación de 'h' inicial perdida por escaneo/OCR
    if not en_diccionario_es(norm) and not norm.startswith('h'):
        candidata_con_h = 'h' + norm
        if any(candidata_con_h.startswith(r) for r in RAICES_H_VALIDAS) and en_diccionario_es(candidata_con_h):
            norm = candidata_con_h

    # 3. Detectar si contenía secuencias anómalas de 3 o más repeticiones consecutivas
    tenia_triples = bool(re.search(r'(.)\1{2,}', norm))

    # Colapsar Faux Bold y letras repetidas anómalas
    corregida = corregir_caracteres_repetidos(norm)

    # Si contenía repeticiones triples o superiores (ej. aaaab, aaabc, zzzz),
    # solo se admite la palabra colapsada si es un término real en diccionario o acrónimo válido.
    if tenia_triples and not en_diccionario_es(corregida) and corregida not in ACRONIMOS_VALIDOS:
        return []

    # 4. Despegar sufijos comunes (ej: abrildel -> abril + del)
    partes = despegar_sufijo_preposicion(corregida)

    # 5. Despegar palabras compuestas pegadas por OCR estrecho (ej: aspectosprincipales -> aspectos + principales)
    partes_desdobladas = []
    for p in partes:
        p_clean = p.strip()
        if len(p_clean) >= 7 and not en_diccionario_es(p_clean) and p_clean not in ACRONIMOS_VALIDOS:
            dividido = False
            for i in range(3, len(p_clean) - 2):
                w1, w2 = p_clean[:i], p_clean[i:]
                if (en_diccionario_es(w1) or w1 in ACRONIMOS_VALIDOS) and (en_diccionario_es(w2) or w2 in ACRONIMOS_VALIDOS):
                    partes_desdobladas.extend([w1, w2])
                    dividido = True
                    break
            if not dividido:
                partes_desdobladas.append(p_clean)
        else:
            partes_desdobladas.append(p_clean)

    # 6. Corrección de erratas ópticas OCR Levenshtein distancia 1 para palabras de longitud >= 5
    palabras_corregidas = []
    for p in partes_desdobladas:
        if not en_diccionario_es(p) and p not in ACRONIMOS_VALIDOS and len(p) >= 5 and _spell:
            cand = _spell.correction(p)
            if cand:
                cand_norm = quitar_tildes(cand.lower())
                if (en_diccionario_es(cand_norm) or cand_norm in ACRONIMOS_VALIDOS) and _distancia_edicion_1(p, cand_norm):
                    palabras_corregidas.append(cand_norm)
                    continue
        palabras_corregidas.append(p)

    palabras_validas = []
    for p in palabras_corregidas:
        p_limpia = p.strip()
        if es_palabra_valida_espanol(p_limpia, stopwords_normalizadas):
            palabras_validas.append(p_limpia)

    return palabras_validas


def extraer_palabras_limpias(texto: str, stopwords_normalizadas: set) -> list[str]:
    """
    Pipeline completo de extracción de palabras limpias de un texto:
    1. Limpieza estructural (de-hyphenation multi-página, apóstrofes, ligaduras).
    2. Extracción de tokens alfabéticos en español (incluye acentuadas, diéresis y eñe).
    3. Normalización, deduplicación de Faux Bold, despegado, recuperación OCR y filtrado fonotáctico.
    """
    if not texto:
        return []

    # 1. Preprocesamiento estructural del texto
    texto_limpio = limpiar_texto_estructural(texto)

    # 2. Extracción de tokens alfabéticos (incluye letras acentuadas, diéresis y eñe)
    tokens = re.findall(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b', texto_limpio)

    # 3. Procesar y filtrar cada palabra
    palabras_finales = []
    for token in tokens:
        validadas = procesar_palabra_individual(token, stopwords_normalizadas)
        palabras_finales.extend(validadas)

    return palabras_finales
