import os
import re
import zipfile
from collections import Counter
from tempfile import TemporaryDirectory

from django.db.models import F
from django.core.files import File

from .models import TotalCountReport, Report, TotalCount
from .stopwords import STOPWORDS_ES
from .utils import (
    quitar_tildes, 
    extraer_texto_pdf_inteligente, 
    encontrar_compañia_año,
    calcular_metricas_complejidad,
    contar_palabras_tecnicas
)

# --- Constantes ---
STOPWORDS_ES_NORMALIZADAS = set(quitar_tildes(p) for p in STOPWORDS_ES)

# --- Funciones utilitarias ---

def count_words(texto: str) -> Counter:
    """Cuenta las palabras en un texto, normalizando y eliminando stopwords."""
    texto = texto.lower()
    palabras = re.findall(r"\b[a-záéíóúüñ]+\b", texto)
    palabras = [quitar_tildes(p) for p in palabras]
    palabras_filtradas = [
        p for p in palabras if len(p) > 2 and p not in STOPWORDS_ES_NORMALIZADAS
    ]
    return Counter(palabras_filtradas)

def find_paragraph(report: Report, palabra: str):
        
    palabra_norm = quitar_tildes(palabra.lower().strip())
    texto = report.extracted_text or ""
    parrafos = re.split(r'\n{2,}|\r\n{2,}', texto)
    resultado = []
    for p in parrafos:
        p_limpio = p.strip()
        if not p_limpio:
            continue
        texto_norm = quitar_tildes(p_limpio.lower())

        ocurrencias = len(re.findall(rf"\b{re.escape(palabra_norm)}\b", texto_norm))

        if ocurrencias > 0:
            resultado.append({
                "paragraph": p_limpio,
                "count": ocurrencias
            })

    return resultado

# --- Funciones principales ---
# Proceso de análisis de cada PDF
def process_report(report_path: str, report_instance: Report):
    texto = extraer_texto_pdf_inteligente(report_path)
    if not texto.strip():

        print(
            f"ERROR: No se pudo extraer texto de {report_path}"
        )

        return
    texto = re.sub(r'\n\s*\n', '<<PARA>>', texto)
    texto = texto.replace('\n', ' ')
    texto = texto.replace('<<PARA>>', '\n\n')
    report_instance.extracted_text = texto
    company, year = encontrar_compañia_año(texto)

    if not report_instance.name:
        report_instance.name = os.path.basename(report_path)
    if not report_instance.company:
        report_instance.company = company
    if not report_instance.year:
        report_instance.year = year
    
    # Calcular métricas de complejidad
    metricas = calcular_metricas_complejidad(texto)
    print("==========")
    print(report_instance.name)
    print(metricas)
    print("==========")
    print("==========")
    print(report_instance.name)
    print("LONGITUD TEXTO:", len(texto))
    print("==========")
    report_instance.total_words = metricas.get("total_words", 0)
    report_instance.unique_words = metricas.get("unique_words", 0)
    report_instance.total_sentences = metricas.get("total_sentences", 0)
    report_instance.avg_word_length = metricas.get("avg_word_length", 0)
    report_instance.avg_sentence_length = metricas.get("avg_sentence_length", 0)
    report_instance.inflesz_score = metricas.get("inverted_inflesz", 0)
    report_instance.total_syllables = metricas.get("total_syllables", 0)
    
    # Contar palabras técnicas
    report_instance.technical_words_count = contar_palabras_tecnicas(texto, year)
    
    report_instance.save()

    conteo = count_words(texto)

    for palabra, cantidad in conteo.items():
        TotalCountReport.objects.update_or_create(
            report=report_instance, word=palabra, defaults={"quantity": cantidad}
        )

        # Solo se actualiza el conteo total, sin importar año o empresa
        obj, creado = TotalCount.objects.get_or_create(
            word=palabra,
            defaults={"quantity": cantidad},
        )
        if not creado:
            TotalCount.objects.filter(pk=obj.pk).update(
                quantity=F("quantity") + cantidad
            )

#Manejo de archivo zip
def process_zip(zip_path: str, company=None):
    with zipfile.ZipFile(zip_path, "r") as zip_ref, TemporaryDirectory() as temp_dir:
        zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for filename in files:
                if not filename.lower().endswith(".pdf"):
                    continue  # Ignora archivos que no son PDF

                file_path = os.path.join(root, filename)

                try:
                    with open(file_path, "rb") as f:
                        django_file = File(f)
                        report = Report(company=company)
                        # Guarda el archivo PDF en MEDIA_ROOT con el nombre original
                        report.file.save(filename, django_file, save=True)

                    # Procesa el reporte con la función que ya tienes
                    process_report(report.file.path, report)

                except Exception as e:
                    print(f"Error procesando {file_path}: {e}")
