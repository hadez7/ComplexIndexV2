# Pestaña de "Índice de Complejidad" - Módulo de Conteo de Palabras

## 📋 Descripción General

Se ha agregado una nueva pestaña llamada **"Índice de Complejidad"** al módulo de conteo total de palabras. Esta pestaña permite visualizar 8 parámetros clave que miden la complejidad de los informes financieros, con filtros dinámicos por año y empresa.

---

## 🎯 Funcionalidades

### 1. **Dos Pestañas Principales**
- **Conteo Total**: Muestra la tabla tradicional de frecuencia de palabras
- **Índice de Complejidad**: Muestra los 8 parámetros de complejidad

### 2. **Información de Contexto**
Cuando está visible la pestaña de complejidad, se muestra:
- **RUC**: Número de identificación de la empresa (si está seleccionada)
- **Nombre de Empresa**: Razón social completa (si está seleccionada, o "Todas")
- **Año**: Año filtrado (o "Todos" si no hay filtro)
- **Cantidad de Reportes**: Número de reportes procesados con los filtros aplicados

### 3. **Los 8 Parámetros de Complejidad**

#### **Parámetros Básicos:**
1. **Total de Palabras** 
   - 📊 Promedio de palabras por informe
   - Mayor valor = documentos más extensos

2. **Palabras Únicas**
   - 📝 Vocabulario promedio usado
   - Indica la variedad de términos

3. **Total de Oraciones**
   - 📄 Número promedio de oraciones
   - Estructura del documento

4. **Longitud Promedio de Palabras**
   - 📏 Caracteres por palabra
   - Mayor = palabras más complejas

5. **Palabras por Oración**
   - 🎯 Promedio de palabras por oración
   - Indicador de densidad sintáctica

6. **Palabras Técnicas**
   - 🔬 Promedio de términos especializados
   - Basado en listas de expertos

#### **Índices Derivados:**
7. **Índice de Diversidad Léxica** (%)
   - Fórmula: (Palabras únicas / Total de palabras) × 100
   - Mayor % = más vocabulario variado
   - Rango: 0-100%

8. **Índice de Legibilidad** (%)
   - Fórmula: 100 - (Palabras por oración)
   - Mayor % = oraciones más cortas = mejor legibilidad
   - Rango: 0-100%

---

## 📊 Cómo Funciona con Filtros

### **Sin Filtros (Todos los años, todas las empresas)**
```
Año: Todos
Empresa: Todas
Parámetros: Promedios calculados sobre TODOS los reportes
```

### **Filtro por Año (Ej: 2023)**
```
Año: 2023
Empresa: Todas
Parámetros: Solo reportes del año 2023
```

### **Filtro por Empresa (Ej: ABSORPELSA)**
```
Año: Todos
Empresa: ABSORPELSA
RUC: 1791353455001
Parámetros: Solo reportes de esa empresa (todos los años)
```

### **Filtro por Año + Empresa**
```
Año: 2023
Empresa: ABSORPELSA
RUC: 1791353455001
Parámetros: Solo reportes de 2023 de esa empresa
```

---

## 🔧 Cambios Técnicos Realizados

### **Backend (`total_count_views.py`)**

#### Nueva función: `get_complexity_metrics(request)`
```python
def get_complexity_metrics(request):
    """
    Calcula métricas de complejidad filtradas por año y empresa.
    
    Retorna diccionario con:
    - total_words_avg: Promedio de palabras totales
    - unique_words_avg: Promedio de palabras únicas
    - total_sentences_avg: Promedio de oraciones
    - avg_word_length: Promedio de caracteres por palabra
    - avg_sentence_length: Promedio de palabras por oración
    - technical_words_avg: Promedio de palabras técnicas
    - diversity_index: Índice de diversidad léxica (%)
    - readability_index: Índice de legibilidad (%)
    - reports_count: Total de reportes procesados
    """
```

#### Vista actualizada: `total_count_view()`
Ahora calcula y pasa al template:
- `complexity_metrics`: Diccionario con los 9 valores
- `selected_company`: Objeto de la empresa seleccionada (o None)

### **Frontend (template `totalcount.html`)**
- Sistema de pestañas con JavaScript
- 8 tarjetas de métrica con colores y iconos
- Sección de información de contexto
- Guía de interpretación
- Mensaje cuando no hay datos

---

## 🎨 Diseño Visual

### Estructura de Pestañas
```
┌────────────────────────────────────────┐
│ 📊 Conteo Total | 📈 Índice de Complejidad │
├────────────────────────────────────────┤
│                                           │
│  Contenido de la pestaña seleccionada    │
│                                           │
└────────────────────────────────────────┘
```

### Tarjetas de Métrica
Cada métrica se muestra en una tarjeta con:
- Título y icono representativo
- Valor principal en grande y osado
- Explicación pequeña del significado
- Bordes de color distintivos

### Colores por Métrica
- **Total de Palabras**: Purple
- **Palabras Únicas**: Blue
- **Oraciones**: Green
- **Longitud Promedio**: Yellow
- **Palabras por Oración**: Red
- **Palabras Técnicas**: Indigo
- **Diversidad Léxica**: Pink
- **Legibilidad**: Teal

---

## 📱 Ejemplo de Uso

### Flujo de usuario:

1. **Accede a "Conteo Total"** desde el panel
2. **Selecciona filtros** (año, empresa, lista de experto)
3. **Hace clic en "Filtrar"**
4. **Ve la pestaña "Conteo Total"** con palabras agrupadas
5. **Hace clic en "Índice de Complejidad"**
6. **Ve los 8 parámetros** con los filtros aplicados
7. **Interpreta los resultados** usando la guía incluida

### Interpretación Práctica:

**Si "Índice de Diversidad Léxica" = 35%:**
- ✅ 35% de vocabulario único
- 📌 El documento reutiliza muchas palabras clave
- 💡 Complejidad léxica = Baja-Media

**Si "Legibilidad" = 25%:**
- ⚠️ Oraciones muy largas (promedio 75 palabras)
- 📌 Difícil de leer y entender
- 💡 Complejidad sintáctica = Alta

**Si "Palabras Técnicas" = 120:**
- ✅ 120 términos especializados encontrados
- 📌 Documento altamente técnico
- 💡 Densidad técnica = Alta

---

## 💡 Casos de Uso

### Análisis Comparativo:
```
"Comparar complejidad entre 2023 y 2023 para la misma empresa"
→ Usar filtros por año para ver evolución temporal
```

### Benchmarking:
```
"¿Cuál es la legibilidad promedio en toda la industria?"
→ Sin filtro de empresa, ver promedio sectorial
```

### Auditoría:
```
"¿El informe de ABSORPELSA 2023 tiene más vocabulario técnico que otros?"
→ Filtrar empresa + año específico
```

---

## ⚠️ Consideraciones Importantes

1. **Los datos dependen de que los reportes hayan sido procesados**
   - Si no hay reportes con los filtros, mostrará: "No hay datos de complejidad"
   
2. **Las métricas se calculan en tiempo real**
   - Basadas en los campos del modelo Report
   - Requiere que los reportes tengan completados: total_words, unique_words, etc.

3. **Interpretación contextual**
   - Los valores "altos" o "bajos" dependen del industria y tipo de documento
   - Usar como referencia comparativa, no como valor absoluto

4. **Performance**
   - Filtrar por empresa específica = consultas más rápidas
   - Filtro "Todos" puede ser lento con muchos reportes

---

## 🔄 Integración con Sistema Existente

La nueva funcionalidad se integra seamlessly con:
- ✅ Sistema de filtros existente (año, empresa, lista de experto)
- ✅ Panel de administración
- ✅ Autenticación de usuarios
- ✅ Modelos de BD (Report, Company, ExpertWord)
- ✅ Exportación a Excel (solo aplica a Conteo Total por ahora)

---

## 📝 Archivos Modificados

1. **Counter/views/total_count_views.py**
   - Agregada función `get_complexity_metrics()`
   - Actualizada vista `total_count_view()`

2. **Counter/templates/totalcount.html**
   - Agregado sistema de pestañas
   - Agregadas tarjetas de métricas
   - Agregada guía de interpretación
   - Agregado JavaScript para funcionalidad de pestañas

---

## 🚀 Próximas Mejoras Sugeridas

1. **Exportación de Complejidad a Excel**
   - Agregar botón de exportación específico para métricas
   
2. **Gráficos Temporales**
   - Línea de tendencia de complejidad por año
   - Radar chart de all 8 metrics

3. **Comparación entre Empresas**
   - Vista lado a lado de complejidad de varias empresas
   - Ranking de empresas por complejidad

4. **Alertas de Complejidad**
   - Notificar cuando legibilidad es muy baja
   - Alertas de vocabulario duplicado excesivo

5. **Machine Learning**
   - Predecir complejidad de nuevos reportes
   - Clustering de reportes por tipo de complejidad

---

versión: 1.0  
fecha: 2026-02-27  
actualizado por: GitHub Copilot
