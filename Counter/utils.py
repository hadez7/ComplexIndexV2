import re
import unicodedata
import base64
import os
from io import BytesIO
from dotenv import load_dotenv
import fitz  # PyMuPDF
import pandas as pd
from openai import OpenAI
from fuzzywuzzy import fuzz
from pdf2image import convert_from_path
from .models import Province, Company, ExpertWord, TotalCountReport
from .models import (
    ConcealmentReview,
    ConcealmentParagraphReview
)
# Cargar variables de entorno desde .env
load_dotenv()

from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

# Extraer texto de PDF digital
def extraer_texto_pdf(path: str) -> str:
    texto = ""
    try:
        with fitz.open(path) as doc:
            for page in doc:
                texto += page.get_text()
    except Exception as e:
        print(f"Error al extraer texto digital con PyMuPDF: {e}")
    return texto 


# Extraer texto de PDF Escaneado usando OCR Local Tesseract (gratuito y sin API externa)
def extraer_texto_ocr_tesseract(path: str) -> str:
    """
    Extrae texto de PDF escaneado utilizando Tesseract OCR local.
    Renderiza cada página en memoria vía PyMuPDF (sin requerir poppler pdftoppm)
    y prioriza el modelo en español ('spa').
    """
    if pytesseract is None:
        print("pytesseract no está disponible en el entorno.")
        return ""

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_tessdata = os.path.join(base_dir, "tessdata")
        config_params = ""
        if os.path.isdir(local_tessdata) and os.path.isfile(os.path.join(local_tessdata, "spa.traineddata")):
            config_params = f'--tessdata-dir "{local_tessdata}"'

        texto_paginas = []
        with fitz.open(path) as doc:
            if len(doc) == 0:
                return ""

            for idx, page in enumerate(doc):
                try:
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(BytesIO(pix.tobytes("png")))

                    # Intentar en español; si el idioma no está disponible, usar inglés o configuración base
                    try:
                        texto_pag = pytesseract.image_to_string(img, lang="spa", config=config_params)
                    except Exception:
                        texto_pag = pytesseract.image_to_string(img, lang="eng", config=config_params)

                    if texto_pag and texto_pag.strip():
                        texto_paginas.append(texto_pag.strip())
                except Exception as e_page:
                    print(f"Error en OCR Tesseract para página {idx + 1}: {e_page}")
                    continue

        return "\n\n".join(texto_paginas).strip()
    except Exception as e:
        print(f"Error general en OCR Tesseract: {e}")
        return ""


# Extraer texto de PDF Escaneado usando OpenAI Vision (gpt-4o-mini) como respaldo secundario
def extraer_texto_ocr_gpt4omini(path: str) -> str:
    """
    Extrae texto de PDF escaneado usando la API de OpenAI (gpt-4o-mini con visión).
    Verifica previamente que OPENAI_API_KEY esté configurada antes de cualquier intento.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        print("OPENAI_API_KEY no configurada. Omitiendo OCR de OpenAI.")
        return ""

    try:
        client = OpenAI(api_key=api_key.strip())
        texto_completo = []

        with fitz.open(path) as doc:
            if len(doc) == 0:
                return ""

            for idx, page in enumerate(doc):
                try:
                    pix = page.get_pixmap(dpi=150)
                    img_base64 = base64.standard_b64encode(pix.tobytes("png")).decode("utf-8")

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{img_base64}"
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": "Extrae TODO el texto de esta imagen en español. Incluye tablas, números y formato. Solo el texto extraído, sin explicaciones ni markdown envolvente."
                                    }
                                ]
                            }
                        ],
                        max_completion_tokens=4000
                    )

                    texto_pagina = response.choices[0].message.content or ""
                    if texto_pagina.strip():
                        texto_completo.append(texto_pagina.strip())
                    print(f"Página {idx + 1}/{len(doc)} procesada con gpt-4o-mini")

                except Exception as e_page:
                    print(f"Error procesando página {idx + 1} con gpt-4o-mini: {e_page}")
                    continue

        return "\n\n".join(texto_completo).strip()
    except Exception as e:
        print(f"Error en OCR con gpt-4o-mini: {e}")
        return ""


# Alias para compatibilidad con llamadas previas
extraer_texto_ocr_gpt5mini = extraer_texto_ocr_gpt4omini


# Extracción de texto inteligente de PDF en capas
def extraer_texto_pdf_inteligente(path: str) -> str:
    """
    Pipeline inteligente en 3 niveles:
    1. Extracción digital nativa con PyMuPDF (rápida y de alta fidelidad).
    2. Si el texto está vacío (PDF escaneado), OCR local gratuito con Tesseract en español.
    3. Si el OCR local no extrajo texto y existe OPENAI_API_KEY, respaldo con OpenAI gpt-4o-mini.
    """
    texto = extraer_texto_pdf(path)
    if not texto or len(texto.strip()) < 30:
        # Nivel 2: OCR local gratuito
        texto_tesseract = extraer_texto_ocr_tesseract(path)
        if texto_tesseract and len(texto_tesseract.strip()) >= 30:
            return texto_tesseract

        # Nivel 3: Respaldo con OpenAI gpt-4o-mini si hay API KEY disponible
        texto_openai = extraer_texto_ocr_gpt4omini(path)
        if texto_openai and texto_openai.strip():
            return texto_openai

        # Retornar lo mejor obtenido
        return texto_tesseract if texto_tesseract else texto

    return texto



from .cleaner import quitar_tildes, limpiar_texto_estructural

def contar_silabas_palabra(palabra: str) -> int:
    """
    Aproximación de conteo de sílabas para español.
    """
    palabra = palabra.lower()

    grupos_vocales = re.findall(
        r'[aeiouáéíóúü]+',
        palabra
    )

    silabas = len(grupos_vocales)

    return max(1, silabas)



#Busca el nombre de empresa y una año en el texto de un PDF. Devuelve valores por defecto si no hay coincidencias
def encontrar_compañia_año(text: str, workspace=None):
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    year = int(year_match.group()) if year_match else None

    best_score = 0
    best_company = None

    if workspace:
        companies = Company.objects.filter(workspace=workspace)
    else:
        companies = Company.objects.all()

    for company in companies:
        score = fuzz.partial_ratio(company.name.lower(), text.lower())
        if score > best_score and score > 60:
            best_score = score
            best_company = company

    return best_company, year


# Patrón para proteger abreviaturas comunes en español (jurídicas, societarias y académicas)
# y letras sueltas con punto (como incisos o iniciales) para no considerarlas fin de oración.
_ABREV_SENTENCE_PATTERN = re.compile(
    r"\b(art|arts|s\.a|c\.a|cia|inc|corp|ltda|dr|dra|sr|sra|pág|págs|pag|pags|ej|etc|núm|num|no|nro|av|tel|ing|lic|prof|dto|dpto|depto|ref|reg|res|sec|gob|cap|coord|univ|vol|vols|[a-záéíóúüñ])\.",
    re.IGNORECASE,
)


#Calcular métricas de complejidad del texto
def calcular_metricas_complejidad(texto: str) -> dict:
    """
    Calcula métricas de complejidad basadas en el texto extraído.
    Retorna un diccionario con:
    - total_words: Total de palabras léxicas
    - unique_words: Palabras únicas
    - total_sentences: Total de oraciones
    - avg_word_length: Longitud promedio de palabras
    - avg_sentence_length: Promedio de palabras por oración
    - total_syllables: Sílabas totales calculadas
    - inflesz: Puntuación de legibilidad INFLESZ / Flesch-Szigriszt (0-100)
    - inverted_inflesz: Factor de opacidad / complejidad inversa (0-1)
    - readability_score: Índice de legibilidad normalizado (0-100)
    """
    if not texto or not texto.strip():
        return {
            "total_words": 0,
            "unique_words": 0,
            "total_sentences": 0,
            "avg_word_length": 0.0,
            "avg_sentence_length": 0.0,
            "total_syllables": 0,
            "inflesz": 0.0,
            "inverted_inflesz": 0.0,
            "readability_score": 0.0,
        }

    # 1. Limpieza estructural previa (de-hyphenation multi-página, ligaduras tipográficas, etc.)
    texto_estructural = limpiar_texto_estructural(texto)
    texto_limpio = texto_estructural.lower().strip()

    # 2. Contar oraciones sin romper abreviaturas comunes (Art., S.A., Inc.) ni cifras decimales
    texto_oraciones = re.sub(r"(\d)\.(\d)", r"\1__NUMDOT__\2", texto_limpio)
    while True:
        nuevo_texto, n = _ABREV_SENTENCE_PATTERN.subn(r"\1__DOT__", texto_oraciones)
        if n == 0:
            break
        texto_oraciones = nuevo_texto
    oraciones = re.split(r"[.!?]+", texto_oraciones)
    oraciones = [s.strip() for s in oraciones if s.strip()]
    total_sentences = len(oraciones) if oraciones else 1

    # 3. Palabras totales para métricas oracionales (incluye palabras gramaticales)
    tokens_oracion = re.findall(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b', texto_estructural)
    total_tokens = len(tokens_oracion) if tokens_oracion else 1

    # 4. Palabras limpias para vocabulario léxico (incluye diéresis y eñe)
    palabras_raw = re.findall(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b', texto_limpio)
    palabras_validas = [quitar_tildes(p) for p in palabras_raw if len(p) >= 3]
    if not palabras_validas:
        palabras_validas = [quitar_tildes(p) for p in palabras_raw]

    total_words = len(palabras_validas) if palabras_validas else total_tokens
    unique_words = len(set(palabras_validas)) if palabras_validas else 1

    # Calcular longitud promedio de palabras y palabras por oración
    avg_word_length = sum(len(p) for p in palabras_validas) / total_words if total_words > 0 else 0
    avg_sentence_length = total_tokens / total_sentences if total_sentences > 0 else 0

    # 5. Calcular sílabas totales (adaptado a lengua española)
    total_syllables = sum(
        contar_silabas_palabra(p)
        for p in tokens_oracion
    )

    # INFLESZ: Fórmula oficial Flesch-Szigriszt adaptada a lengua española
    # INFLESZ = 206.84 - 0.623 * (sílabas / palabras * 100) - (palabras / oraciones)
    syllables_per_100_words = (
        (total_syllables / total_tokens) * 100
        if total_tokens > 0 else 0
    )
    words_per_sentence = avg_sentence_length

    inflesz = (
        206.84
        - (0.623 * syllables_per_100_words)
        - words_per_sentence
    )

    # Normalización a escala 0-100 para legibilidad
    readability_score = max(0.0, min(100.0, inflesz))

    # Inversión de legibilidad a factor de complejidad (0-1: 0 = simple, 1 = complejo)
    inverted_inflesz = max(0.0, min(1.0, 1.0 - (readability_score / 100.0)))

    return {
        "total_words": total_words,
        "unique_words": unique_words,
        "total_sentences": total_sentences,
        "avg_word_length": round(avg_word_length, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "total_syllables": total_syllables,
        "inflesz": round(inflesz, 2),
        "readability_score": round(readability_score, 1),
        "inverted_inflesz": round(inverted_inflesz, 3),
    }

#Contar palabras técnicas basadas en listas de expertos
def contar_palabras_tecnicas(texto: str, year: int = None, workspace=None) -> int:
    """
    Cuenta cuántas palabras del texto están en las listas de palabras técnicas de expertos.
    Incluye caracteres en español con diéresis (ü) y eñe (ñ), con coincidencia canónica y normalizada.
    Filtra estrictamente por el espacio de trabajo indicado.
    """
    if not texto or not texto.strip():
        return 0

    # Extraer palabras del texto incluyendo diéresis y eñe
    palabras_texto_raw = set(re.findall(r"\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+(?:\'[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)?\b", texto))
    palabras_texto = {p.lower() for p in palabras_texto_raw}
    palabras_texto_norm = {quitar_tildes(p) for p in palabras_texto}

    # Listas de palabras técnicas: estrictamente las del espacio de trabajo indicado.
    if workspace:
        listas_expertos = ExpertWord.objects.filter(workspace=workspace)
    else:
        listas_expertos = ExpertWord.objects.none()

    palabras_tecnicas_encontradas = set()

    for lista in listas_expertos:
        if lista.words:
            for palabra_tecnica in lista.words:
                pt_lower = str(palabra_tecnica).lower().strip()
                pt_norm = quitar_tildes(pt_lower)
                # Coincidencia directa o insensible a tildes
                if pt_lower in palabras_texto or pt_norm in palabras_texto_norm:
                    palabras_tecnicas_encontradas.add(pt_lower)

    return len(palabras_tecnicas_encontradas)

#Calcular complejidad general compuesta (escala 0-1)
def calcular_complejidad_general(diversidad_lexica: float, legibilidad: float, densidad_tecnica: float) -> float:
    """
    Calcula el índice de complejidad general combinando tres parámetros.
    Todos los parámetros deben estar en escala 0-1.

    Fórmula: 
    Complejidad General = (Diversidad Léxica + (1 - Legibilidad) + Densidad Técnica) / 3

    Parámetros:
    - diversidad_lexica: unique_words / total_words (0-1)
    - legibilidad: legibilidad del documento en escala 0-1 (donde 1=legible, 0=no legible / opaco)
    - densidad_tecnica: technical_words / total_words (0-1)

    Retorna un valor entre 0 y 1:
    - Cercano a 0: Documento simple (baja complejidad)
    - Cercano a 0.5: Complejidad media
    - Cercano a 1: Documento muy complejo (alta complejidad)
    """
    diversidad_lexica = max(0.0, min(1.0, float(diversidad_lexica or 0)))
    legibilidad = max(0.0, min(1.0, float(legibilidad or 0)))
    densidad_tecnica = max(0.0, min(1.0, float(densidad_tecnica or 0)))

    # Inverso de legibilidad: menor legibilidad (texto difícil) incrementa la complejidad
    inverso_legibilidad = 1.0 - legibilidad
    complejidad = (diversidad_lexica + inverso_legibilidad + densidad_tecnica) / 3.0

    return round(complejidad, 3)


#Cargar empresas desde un archivo Excel
def insertar_empresas(archivo_excel, workspace):
    """
    Importa empresas desde un Excel hacia el espacio de trabajo indicado.
    `workspace` es obligatorio: las empresas siempre pertenecen a un espacio.
    """
    if workspace is None:
        raise ValueError("insertar_empresas requiere un workspace destino.")

    df = pd.read_excel(archivo_excel)

    for _, row in df.iterrows():
        nombre_empresa = row["NOMBRE DE LA ENTIDAD"]
        ruc_empresa = row["IDENTIFICACIÓN"]
        nombre_provincia = row["provincia"]

        provincia, _ = Province.objects.get_or_create(name=nombre_provincia)

        if not Company.objects.filter(
            workspace=workspace, name=nombre_empresa
        ).exists() and not Company.objects.filter(
            workspace=workspace, ruc=ruc_empresa
        ).exists():
            Company.objects.create(
                workspace=workspace,
                name=nombre_empresa, ruc=ruc_empresa, province=provincia
            )
        else:
            print(
                f"Empresa '{nombre_empresa}' con RUC '{ruc_empresa}' ya existe. No se insertó."
            )

    print("Empresas importadas correctamente.")

def recalcular_metricas_reporte(report):

    texto = report.extracted_text or ""

    if not texto.strip():
        return

    # Obtener la última revisión de cada palabra
    revisiones = {}

    for review in (
        ConcealmentReview.objects
        .filter(report=report)
        .order_by("word", "-reviewed_at")
    ):

        if review.word not in revisiones:
            revisiones[review.word] = review

    texto_modificado = texto

    for palabra, review in revisiones.items():

        descartados = ConcealmentParagraphReview.objects.filter(
            review=review,
            discarded=True
        )

        palabra_norm = re.escape(
            quitar_tildes(
                palabra.lower()
            )
        )

        for parrafo in descartados:

            texto_parrafo = parrafo.paragraph_text

            texto_parrafo_modificado = re.sub(
                rf"\b{palabra_norm}\b",
                "",
                quitar_tildes(texto_parrafo.lower()),
                flags=re.IGNORECASE
            )

            texto_modificado = texto_modificado.replace(
                texto_parrafo,
                texto_parrafo_modificado
            )

    # Recalcular métricas usando el texto ajustado
    metricas = calcular_metricas_complejidad(
        texto_modificado
    )

    report.total_words = metricas["total_words"]
    report.unique_words = metricas["unique_words"]
    report.total_sentences = metricas["total_sentences"]
    report.avg_word_length = metricas["avg_word_length"]
    report.avg_sentence_length = metricas["avg_sentence_length"]
    report.inflesz_score = metricas["inverted_inflesz"]
    report.total_syllables = metricas["total_syllables"]

    report.technical_words_count = contar_palabras_tecnicas(
        texto_modificado,
        report.year,
        workspace=report.workspace
    )

    report.save()