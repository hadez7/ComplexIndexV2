# Implementación de GPT-5-mini para OCR y Métricas de Complejidad

## 🔄 Cambios Realizados

### 1. **Modelo Report Actualizado**
Se agregaron 6 nuevos campos al modelo `Report` para almacenar métricas de complejidad:

```python
- total_words: PositiveIntegerField - Total de palabras en el documento
- unique_words: PositiveIntegerField - Cantidad de palabras únicas
- total_sentences: PositiveIntegerField - Total de oraciones
- avg_word_length: FloatField - Longitud promedio de palabras
- avg_sentence_length: FloatField - Promedio de palabras por oración
- technical_words_count: PositiveIntegerField - Palabras técnicas encontradas
```

### 2. **OCR Reemplazado: pytesseract → GPT-5-mini**

#### Ventajas:
✅ **Mayor precisión** en documentos escaneados complejos  
✅ **Mejor OCR** para jerga financiera y caracteres especiales  
✅ **Sin dependencias de sistema** (pytesseract requería instalación de Tesseract)  
✅ **Bilingüe automático** (maneja español e inglés)  

#### Función Principal:
```python
def extraer_texto_ocr_gpt5mini(path: str) -> str:
    """
    Extrae texto usando GPT-5-mini Vision API.
    - Requiere OPENAI_API_KEY en variables de entorno
    - Procesa PDF página por página
    - Retorna texto completo normalizado
    """
```

### 3. **Nuevas Funciones en utils.py**

#### `calcular_metricas_complejidad(texto: str) -> dict`
Calcula 5 métricas de complejidad:
- **total_words**: Cantidad total de palabras
- **unique_words**: Palabras únicas (vocabulario)
- **total_sentences**: Cantidad de oraciones
- **avg_word_length**: Promedio de caracteres por palabra
- **avg_sentence_length**: Promedio de palabras por oración

#### `contar_palabras_tecnicas(texto: str, year: int = None) -> int`
Cuenta palabras del dominio técnico/financiero:
- Busca palabras en listas de expertos (ExpertWord)
- Puede filtrar por año
- Retorna cantidad de palabras técnicas encontradas

### 4. **Pipeline Automático**
Cuando se procesa un PDF, ahora automáticamente:

```
1. Extrae texto (digital o escaneado con GPT-5-mini)
2. Identifica empresa y año
3. Calcula 6 métricas de complejidad
4. Cuenta palabras técnicas
5. Contabiliza frecuencia de palabras
6. Actualiza TotalCount y TotalCountReport
```

---

## 📋 Configuración Necesaria

### Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto:

```bash
OPENAI_API_KEY=your-api-key-here
```

O establécelas en el sistema:
```powershell
# PowerShell
$env:OPENAI_API_KEY = "tu-api-key"

# CMD
set OPENAI_API_KEY=tu-api-key
```

### Instalar Dependencias
```bash
pip install -r requirements.txt
# Si ya está instalado, solo openai se agregó
pip install openai==1.62.0
```

### Aplicar Migraciones
```bash
python manage.py migrate
```

---

## 💰 Costo de GPT-5-mini

| Elemento | Costo |
|----------|-------|
| Input | $0.25 / 1M tokens |
| Output | $2.00 / 1M tokens |
| **PDF 50 páginas** | ~$0.50 |
| **300 PDFs de 50 pág.** | ~$150/mes |

**Estimación:** Muy económico comparado con soluciones OCR premium.

---

## 🔧 Uso en Código

### Procesar un Reporte Individual
```python
from Counter.main import process_report
from Counter.models import Report

report = Report.objects.create(
    file=django_file,
    company=company_instance,
    year=2024
)

process_report(report.file.path, report)

# Ahora puedes acceder a las métricas:
print(f"Total de palabras: {report.total_words}")
print(f"Palabras únicas: {report.unique_words}")
print(f"Longitud promedio: {report.avg_word_length}")
print(f"Palabras técnicas: {report.technical_words_count}")
```

### Procesar ZIP con Múltiples PDFs
```python
from Counter.main import process_zip

process_zip("ruta/archivo.zip", company=company_instance)
```

### Extraer Texto Manualmente
```python
from Counter.utils import extraer_texto_pdf_inteligente

# Automáticamente trata PDF digital o escaneado
texto = extraer_texto_pdf_inteligente("ruta/archivo.pdf")
```

### Calcular Métricas Manualmente
```python
from Counter.utils import calcular_metricas_complejidad

texto = "Tu contenido..."
metricas = calcular_metricas_complejidad(texto)

print(metricas)
# {
#     'total_words': 1500,
#     'unique_words': 450,
#     'total_sentences': 45,
#     'avg_word_length': 5.2,
#     'avg_sentence_length': 33.3
# }
```

---

## 📊 Filtros por Año en Vistas

Ejemplo para calcular métricas filtradas por año:

```python
from django.db.models import Avg
from Counter.models import Report

# Todos los años
avg_total_words = Report.objects.aggregate(Avg('total_words'))['total_words__avg']

# Año específico
year = 2023
metricas_2023 = Report.objects.filter(year=year).aggregate(
    avg_palabras=Avg('total_words'),
    avg_longitud=Avg('avg_word_length'),
    avg_tecnicas=Avg('technical_words_count'),
    avg_complejidad=Avg('avg_sentence_length'),
    diversidad=Avg('unique_words')
)
```

---

## ⚠️ Consideraciones

1. **API Key Segura**: Nunca guardes la API key en Git. Usa `.env` y `.gitignore`

2. **Rate Limits**: OpenAI tiene límites de requests. Para muchos PDFs, usa batch processing

3. **Errores de Red**: Si falla OpenAI, la función retorna texto vacío. Considera reintentos

4. **Costo de PDF Largo**: Documentos >100 páginas pueden ser costosos. Evalúa según necesidades

5. **Palabras Técnicas**: Asegúrate de que `ExpertWord` está poblada para buenos resultados

---

## 🧪 Testing

Para probar las funciones sin procesar PDF completo:

```python
from Counter.utils import calcular_metricas_complejidad

# Texto de prueba
test_text = """
Este es un texto de prueba. Contiene varias palabras. 
Los informes financieros son complejos. El análisis requiere atención.
Las métricas estadísticas ayudan a evaluar la complejidad.
"""

metricas = calcular_metricas_complejidad(test_text)
print(metricas)
```

---

## 📝 Próximos Pasos Recomendados

1. Implementar interfaz de filtros por año en las vistas
2. Crear gráficos de evolución temporal de métricas
3. Agregar benchmarks de complejidad (bajo, medio, alto)
4. Integrar con análisis de concealment detection
5. Crear reportes comparativos entre empresas y años

---

## ❓ FAQ

**P: ¿Funciona con PDFs password-protected?**  
R: Necesitarías desbloquearlos primero. PyMuPDF puede intentarlo.

**P: ¿Qué si se agota el límite de requests?**  
R: Implementa cola de procesamiento (Celery) o batch API de OpenAI.

**P: ¿Se pueden procesar idiomas además de español?**  
R: Sí, GPT-5-mini es multilingüe. Funciona con cualquier idioma.

**P: ¿Cuánto tiempo tarda procesar un PDF?**  
R: ~1-3 segundos por página (depende de la red).

---

versión: 1.0  
fecha: 2026-02-27
