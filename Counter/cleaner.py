"""
Módulo de limpieza estructural, normalización léxica y saneamiento fonotáctico
para extracción de palabras en documentos PDF y auditoría lingüística.
"""
import re
import unicodedata

# Regex para números romanos (i, ii, iii, iv, v, vi, vii, viii, ix, x, xi, xii, etc.)
ROMAN_REGEX = re.compile(
    r'^(?:m{0,4}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3}))$',
    re.IGNORECASE
)

# Grupos consonánticos de 4 letras legítimos en español (ej: nscr en inscripción, nstr en construcción)
CONSONANTES_VALIDAS_4 = {'nstr', 'nscr', 'rstr', 'bstr', 'dstr', 'pstr', 'ntr', 'ndr', 'mpr', 'mpl'}

# Letras que se pueden doblar legítimamente en palabras del español (ej: acción, leer, coordinar, perro, llave, innovar)
LETRAS_DOBLES_VALIDAS = {'c', 'e', 'o', 'r', 'l', 'n'}

# Palabras legítimas del español o extranjeras que terminan en 'del'
PALABRAS_GENUINAS_DEL = {
    'redondel', 'cordel', 'bedel', 'burdel', 'fidel', 'claudel', 'model', 
    'edel', 'andel', 'rondel', 'candela', 'mendel', 'haendel'
}

# Acrónimos y entidades corporativas legítimas comunes en el ecosistema financiero
ACRONIMOS_VALIDOS = {'bvq', 'bvg', 'scvs', 'biess', 'sri', 'iess', 'pwc', 'deloitte', 'kpmg', 'ey', 'bce', 'cfn'}

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
}


def quitar_tildes(texto: str) -> str:
    """Elimina tildes y diacríticos preservando caracteres base en español."""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def limpiar_texto_estructural(texto: str) -> str:
    """
    Limpieza a nivel de documento antes de la tokenización:
    1. Reúne palabras partidas por guión al final de línea (de-hyphenation).
    2. Fusiona apóstrofes o comillas internas que mutilan palabras (h'abitaciones -> habitaciones).
    3. Separa números pegados a letras (19abril -> 19 abril, abril2024 -> abril 2024).
    4. Corrige símbolos OCR en medio de palabras (acco¡islas -> accoiislas).
    5. Normaliza ligaduras tipográficas (ﬁ -> fi, ﬂ -> fl).
    """
    if not texto:
        return ""

    # Normalización de ligaduras tipográficas
    texto = texto.replace('ﬁ', 'fi').replace('ﬂ', 'fl').replace('ﬀ', 'ff').replace('ﬃ', 'ffi').replace('ﬄ', 'ffl')

    # 1. Reunir palabras partidas por guión de fin de línea
    texto = re.sub(r'([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)-\s*\n\s*([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)', r'\1\2', texto)

    # 2. Despegar números y letras pegadas (ej. 19de abrildel 2024 -> 19 de abrildel 2024)
    texto = re.sub(r'(\d+)([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)', r'\1 \2', texto)
    texto = re.sub(r'([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)(\d+)', r'\1 \2', texto)

    # 3. Eliminar apóstrofes o comillas dentro de palabras (ej. h'abitaciones -> habitaciones, d'e -> de)
    texto = re.sub(r"(?<=[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ])['`´’‘](?=[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ])", "", texto)

    # 4. Sustituir caracteres de exclamación o barra vertical en medio de letras por 'i'
    texto = re.sub(r'(?<=[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ])[¡!|](?=[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ])', 'i', texto)

    return texto


def corregir_caracteres_repetidos(word: str) -> str:
    """
    Corrige anomalías de Faux-Bold y letras triplicadas:
    - Reduce 3 o más letras iguales a 2 (para c,e,o,r,l,n) o 1 (para las demás).
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
    1. Longitud entre 3 y 24 caracteres (más de 24 son oraciones pegadas).
    2. Admite acrónimos y entidades corporativas válidas (bvq, bvg, scvs, deloitte, biess).
    3. Debe contener al menos una vocal o 'y'.
    4. No debe ser número romano (iii, viii, xxxiv, etc.).
    5. 'q' siempre debe ir acompañada de 'u'.
    6. No debe tener secuencias de 4 o más consonantes a menos que pertenezcan a grupos válidos.
    7. No debe ser stopword normalizada.
    8. No debe consistir en el mismo carácter repetido (ej: aaa, zzz).
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
    if not re.search(r'[aeiouy]', word):
        return False

    # Descartar si el mismo carácter forma toda la palabra
    if len(set(word)) == 1:
        return False

    # Regla del español: 'q' siempre debe ir seguida de 'u'
    if 'q' in word and not re.search(r'qu[aeio]', word):
        return False

    # Combinaciones iniciales imposibles en español
    if re.match(r'^(ql|qv|qr|qp|qk|xd|zz|vv|jj|ww)', word):
        return False

    # Descartar secuencias de 4 o más consonantes consecutivas si no pertenecen a grupos válidos
    consonantes_consecutivas = re.findall(r'[^aeiouyáéíóúüñ]{4,}', word)
    for grupo in consonantes_consecutivas:
        if len(grupo) > 4 or (len(grupo) == 4 and grupo not in CONSONANTES_VALIDAS_4):
            return False

    # Descartar stopwords
    if word in stopwords_normalizadas:
        return False

    return True


def procesar_palabra_individual(token: str, stopwords_normalizadas: set) -> list[str]:
    """
    Normaliza y valida un token individual extraído del texto o de la base de datos.
    Devuelve una lista de 0, 1 o más palabras válidas resultantes.
    """
    norm = quitar_tildes(token.lower().strip())
    if len(norm) < 3:
        return []

    # 1. Reemplazo directo de artefactos recurrentes documentados
    if norm in ARTEFACTOS_RECURRENTES:
        norm = ARTEFACTOS_RECURRENTES[norm]

    # 2. Colapsar Faux Bold y letras repetidas anómalas
    corregida = corregir_caracteres_repetidos(norm)

    # 3. Despegar sufijos comunes (ej: abrildel -> abril + del)
    partes = despegar_sufijo_preposicion(corregida)

    palabras_validas = []
    for p in partes:
        p_limpia = p.strip()
        if es_palabra_valida_espanol(p_limpia, stopwords_normalizadas):
            palabras_validas.append(p_limpia)

    return palabras_validas


def extraer_palabras_limpias(texto: str, stopwords_normalizadas: set) -> list[str]:
    """
    Pipeline completo de extracción de palabras limpias de un texto:
    1. Limpieza estructural (de-hyphenation, apóstrofes, ligaduras).
    2. Extracción de tokens primarios alfabéticos en español.
    3. Normalización, deduplicación de Faux Bold, despegado y filtrado fonotáctico.
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

