import os
import re
import zipfile
from collections import Counter
from tempfile import TemporaryDirectory

from django.db import transaction
from django.db.models import Sum
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


def sincronizar_palabras_total_count(palabras):
    """
    Sincroniza de forma matemáticamente exacta la tabla TotalCount
    con la suma real de todos los TotalCountReport vigentes para las palabras dadas.
    Evita la acumulación duplicada o palabras fantasma tras eliminaciones.
    """
    if not palabras:
        return

    palabras_lista = list(palabras)
    chunk_size = 500  # Procesa en lotes para respetar límites de parámetros SQL en SQLite
    for i in range(0, len(palabras_lista), chunk_size):
        chunk = palabras_lista[i:i + chunk_size]
        sumas = (
            TotalCountReport.objects
            .filter(word__in=chunk)
            .values("word")
            .annotate(total=Sum("quantity"))
        )
        totales_dict = {item["word"]: item["total"] for item in sumas}

        for p in chunk:
            tot = totales_dict.get(p, 0)
            if tot > 0:
                TotalCount.objects.update_or_create(
                    word=p,
                    defaults={"quantity": tot}
                )
            else:
                TotalCount.objects.filter(word=p).delete()


# --- Funciones principales ---

def process_report(report_path: str, report_instance: Report) -> dict:
    """
    Procesa un reporte PDF individual:
    - Extrae texto digital u OCR si corresponde.
    - Calcula métricas lingüísticas y de complejidad.
    - Actualiza TotalCountReport y sincroniza TotalCount sin duplicaciones.
    - Ejecutado en transacción atómica para consistencia total.
    """
    try:
        with transaction.atomic():
            texto = extraer_texto_pdf_inteligente(report_path)
            if not texto or not texto.strip():
                report_instance.save()
                return {
                    "success": False,
                    "warning": "No se pudo extraer texto digital del documento PDF. Podría tratarse de un archivo protegido, vacío o escaneado sin OCR.",
                    "total_words": 0
                }

            texto = re.sub(r'\n\s*\n', '<<PARA>>', texto)
            texto = texto.replace('\n', ' ')
            texto = texto.replace('<<PARA>>', '\n\n')
            report_instance.extracted_text = texto
            company, year = encontrar_compañia_año(texto)

            if not report_instance.name:
                report_instance.name = os.path.basename(report_path)
            if not report_instance.company and company:
                report_instance.company = company
            if not report_instance.year and year:
                report_instance.year = year

            # Calcular métricas de complejidad
            metricas = calcular_metricas_complejidad(texto)
            report_instance.total_words = metricas.get("total_words", 0)
            report_instance.unique_words = metricas.get("unique_words", 0)
            report_instance.total_sentences = metricas.get("total_sentences", 0)
            report_instance.avg_word_length = metricas.get("avg_word_length", 0)
            report_instance.avg_sentence_length = metricas.get("avg_sentence_length", 0)
            report_instance.inflesz_score = metricas.get("inverted_inflesz", 0)
            report_instance.total_syllables = metricas.get("total_syllables", 0)

            # Contar palabras técnicas
            report_instance.technical_words_count = contar_palabras_tecnicas(texto, report_instance.year)
            report_instance.save()

            # Obtener palabras anteriores asociadas a este reporte (si se está sobrescribiendo)
            palabras_previas = set(
                TotalCountReport.objects.filter(report=report_instance).values_list("word", flat=True)
            )

            conteo = count_words(texto)
            palabras_actuales = set(conteo.keys())

            # Eliminar palabras previas que ya no existan en el nuevo texto
            palabras_eliminadas = palabras_previas - palabras_actuales
            if palabras_eliminadas:
                TotalCountReport.objects.filter(report=report_instance, word__in=palabras_eliminadas).delete()

            # Actualizar o crear registros por reporte
            for palabra, cantidad in conteo.items():
                TotalCountReport.objects.update_or_create(
                    report=report_instance, word=palabra, defaults={"quantity": cantidad}
                )

            # Sincronizar TotalCount de forma exacta para todas las palabras afectadas
            todas_afectadas = palabras_previas | palabras_actuales
            sincronizar_palabras_total_count(todas_afectadas)

            return {
                "success": True,
                "total_words": report_instance.total_words,
                "unique_words": report_instance.unique_words,
                "message": f"Reporte '{report_instance.name}' procesado correctamente ({report_instance.total_words} palabras)."
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def process_zip(zip_path: str, company=None, overwrite=False) -> dict:
    """
    Manejo robusto de archivo ZIP:
    - Filtra carpetas de sistema (ej: __MACOSX) y archivos temporales (._*).
    - Permite omitir o sobrescribir duplicados.
    - Devuelve resumen estadístico de la importación.
    """
    processed = 0
    skipped = 0
    errors = []

    with zipfile.ZipFile(zip_path, "r") as zip_ref, TemporaryDirectory() as temp_dir:
        zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            if "__MACOSX" in root:
                continue

            for filename in sorted(files):
                if filename.startswith(".") or filename.startswith("._") or not filename.lower().endswith(".pdf"):
                    continue

                file_path = os.path.join(root, filename)

                try:
                    # Validar si ya existe un reporte con el mismo nombre para la empresa
                    existing_report = None
                    if company:
                        existing_report = Report.objects.filter(company=company, name=filename).first()

                    if existing_report and not overwrite:
                        skipped += 1
                        continue

                    with open(file_path, "rb") as f:
                        django_file = File(f)
                        if existing_report and overwrite:
                            report = existing_report
                            report.file.save(filename, django_file, save=False)
                        else:
                            report = Report(company=company, name=filename)
                            report.file.save(filename, django_file, save=False)
                        report.save()

                    res = process_report(report.file.path, report)
                    if res.get("success"):
                        processed += 1
                    elif res.get("warning"):
                        errors.append(f"{filename}: {res['warning']}")
                    else:
                        errors.append(f"{filename}: {res.get('error', 'Error en extracción')}")
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")

    return {
        "processed": processed,
        "skipped": skipped,
        "errors": errors
    }
