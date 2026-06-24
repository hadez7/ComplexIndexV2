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

#Extraer texto de PDF digital
def extraer_texto_pdf(path: str) -> str:
    texto = ""
    with fitz.open(path) as doc:
        for page in doc:
            texto += page.get_text()
    return texto 


#Extraer texto de PDF Escaneado usando GPT-5-mini
def extraer_texto_ocr_gpt5mini(path: str) -> str:
    """
    Extrae texto de PDF escaneado usando la API de OpenAI GPT-5-mini con visión.
    Convierte el PDF a imágenes y las procesa.
    Requiere OPENAI_API_KEY en las variables de entorno.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY no está configurada en las variables de entorno")
        
        client = OpenAI(api_key=api_key)
        
        # Convertir PDF a imágenes
        paginas = convert_from_path(path)
        
        if not paginas:
            print("El PDF no contiene páginas")
            return ""
        
        texto_completo = ""
        
        # Procesar cada página
        for idx, img in enumerate(paginas):
            try:
                # Convertir imagen a base64
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_base64 = base64.standard_b64encode(img_byte_arr.getvalue()).decode('utf-8')
                
                # Enviar a GPT-5-mini Vision API
                response = client.chat.completions.create(
                    model="gpt-5-mini",
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
                                    "text": "Extrae TODO el texto de esta imagen en español. Incluye tablas, números y formato. Solo el texto extraído, sin explicaciones."
                                }
                            ]
                        }
                    ],
                    max_completion_tokens=2000
                )
                
                texto_pagina = response.choices[0].message.content
                texto_completo += texto_pagina + "\n"
                print(f"Página {idx + 1}/{len(paginas)} procesada correctamente")
                
            except Exception as e:
                print(f"Error procesando página {idx + 1}: {str(e)}")
                continue
        
        return texto_completo.strip()
        
    except Exception as e:
        print(f"Error en OCR con GPT-5-mini: {str(e)}")
        return ""


#Verificar si el PDF es digital o escaneado
def extraer_texto_pdf_inteligente(path: str) -> str:
    texto = extraer_texto_pdf(path)
    if not texto.strip():  
        texto = extraer_texto_ocr_gpt5mini(path)
    return texto


#Quita tildes y diacriticos de una palabra
def quitar_tildes(palabra: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFD", palabra)
        if unicodedata.category(c) != "Mn"
    )

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
def encontrar_compañia_año(text: str):
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    year = int(year_match.group()) if year_match else None

    best_score = 0
    best_company = None

    companies = Company.objects.all()
    for company in companies:
        score = fuzz.partial_ratio(company.name.lower(), text.lower())
        if score > best_score and score > 60:
            best_score = score
            best_company = company

    return best_company, year


#Calcular métricas de complejidad del texto
def calcular_metricas_complejidad(texto: str) -> dict:
    """
    Calcula métricas de complejidad basadas en el texto extraído.
    Retorna un diccionario con:
    - total_words: Total de palabras
    - unique_words: Palabras únicas
    - total_sentences: Total de oraciones
    - avg_word_length: Longitud promedio de palabras
    - avg_sentence_length: Promedio de palabras por oración
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
            "inverted_inflesz": 0.0
        }
    
    # Normalizar texto
    texto_limpio = texto.lower().strip()
    
    # Contar oraciones (por puntos, signos de interrogación, exclamación)
    oraciones = re.split(r'[.!?]+', texto_limpio)
    oraciones = [s.strip() for s in oraciones if s.strip()]
    total_sentences = len(oraciones) if oraciones else 1
    
    # Extraer palabras (solo palabras significativas)
    palabras = re.findall(r'\b[a-záéíóúñ]+(?:\'[a-záéíóúñ]+)?\b', texto_limpio)
    total_words = len(palabras)
    unique_words = len(set(palabras))
    
    # Calcular longitud promedio de palabras
    avg_word_length = sum(len(p) for p in palabras) / total_words if total_words > 0 else 0
    
    # Calcular palabras por oración
    avg_sentence_length = total_words / total_sentences if total_sentences > 0 else 0

    # Calcular sílabas totales
    total_syllables = sum(
        contar_silabas_palabra(p)
        for p in palabras
    )

    # INFLESZ
    words_per_sentence = avg_sentence_length

    syllables_per_100_words = (
        (total_syllables / total_words) * 100
        if total_words > 0 else 0
    )

    inflesz = (
        206.84
        - (0.60 * syllables_per_100_words)
        - (1.02 * words_per_sentence)
    )

    # Normalización 0-1
    inflesz_normalized = max(
        0,
        min(1, inflesz / 100)
    )

    # Inversión
    inverted_inflesz = 1 - inflesz_normalized


    
    return {
        "total_words": total_words,
        "unique_words": unique_words,
        "total_sentences": total_sentences,
        "avg_word_length": round(avg_word_length, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),

        "total_syllables": total_syllables,
        "inflesz": round(inflesz, 2),
        "inverted_inflesz": round(inverted_inflesz, 3)
    }

#Contar palabras técnicas basadas en listas de expertos
def contar_palabras_tecnicas(texto: str, year: int = None) -> int:
    """
    Cuenta cuántas palabras del texto están en las listas de palabras técnicas de expertos.
    Si se proporciona un año, considera solo palabras técnicas relevantes para ese período.
    """
    if not texto or not texto.strip():
        return 0
    
    # Extraer palabras del texto
    palabras_texto = set(re.findall(r'\b[a-záéíóúñ]+(?:\'[a-záéíóúñ]+)?\b', texto.lower()))
    
    # Obtener listas de palabras técnicas de expertos
    listas_expertos = ExpertWord.objects.all()
    
    palabras_tecnicas_encontradas = set()
    
    for lista in listas_expertos:
        if lista.words:
            for palabra_tecnica in lista.words:
                palabra_tecnica_lower = str(palabra_tecnica).lower()
                # Buscar coincidencias exactas
                if palabra_tecnica_lower in palabras_texto:
                    palabras_tecnicas_encontradas.add(palabra_tecnica_lower)
    

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
    - legibilidad: 1 - (avg_sentence_length / max_length) (0-1, donde 1=legible, 0=no legible)
    - densidad_tecnica: technical_words / total_words (0-1)
    
    Retorna un valor entre 0 y 1:
    - Cercano a 0: Documento simple (baja complejidad)
    - Cercano a 0.5: Complejidad media
    - Cercano a 1: Documento muy complejo (alta complejidad)
    """
    # Asegurar que los valores están en rango 0-1
    diversidad_lexica = max(0, min(1, diversidad_lexica))
    legibilidad = max(0, min(1, legibilidad))
    densidad_tecnica = max(0, min(1, densidad_tecnica))
    
    # Fórmula: promedio de diversidad, inverso de legibilidad (más difícil = más complejo), y densidad técnica
    complejidad = (diversidad_lexica + legibilidad + densidad_tecnica) / 3
    
    return round(complejidad, 3)


#Cargar empresas desde un archivo Excel
def insertar_empresas(archivo_excel):
    df = pd.read_excel(archivo_excel)

    for _, row in df.iterrows():
        nombre_empresa = row["NOMBRE DE LA ENTIDAD"]
        ruc_empresa = row["IDENTIFICACIÓN"]
        nombre_provincia = row["provincia"]

        provincia, _ = Province.objects.get_or_create(name=nombre_provincia)

        if (
            not Company.objects.filter(name=nombre_empresa).exists()
            and not Company.objects.filter(ruc=ruc_empresa).exists()
        ):
            Company.objects.create(
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
        report.year
    )

    report.save()