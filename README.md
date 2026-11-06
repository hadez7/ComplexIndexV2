# ELI — Enterprise Lex Index

> **Plataforma Integral de Auditoría Lingüística, Complejidad Contractual y Análisis Léxico Multivariante.**

ELI es una solución diseñada para evaluar la complejidad lingüística, detectar riesgos de opacidad normativa y contrastar reportes corporativos contra marcos periciales mediante algoritmos cuantitativos y estadística multivariante.

---

## 💻 Stack Tecnológico

| Capa | Tecnologías |
|---|---|
| **Backend & Web** | Python 3.13 · Django 5.2.1 · SQLite / PostgreSQL |
| **Estadística & NLP** | NumPy · Pipeline léxico de lematización y desguionización multilínea · Stopwords personalizadas |
| **Ingesta & OCR** | PyMuPDF (`fitz`) · Tesseract OCR local · Poppler (`pdftoppm`) · OpenAI Vision (respaldo) · OpenPyXL |
| **Frontend & UI** | Sistema de diseño ELI · Tailwind CSS · Vanilla JS modular · SVG interactivo · Manrope & JetBrains Mono |
| **Internacionalización**| GNU Gettext (bilingüe Español / Inglés al 100%) |

---

## 🚀 Módulos Principales

1. **Observatorio Ejecutivo (Dashboard)**:
   - Panel de control en tiempo real con *Signal Board* de telemetría léxica.
   - Indicadores agregados de diversidad léxica, densidad técnica, legibilidad (INFLESZ) y estado del corpus documental.
2. **Ingesta Documental y Pipeline OCR**:
   - Procesamiento de archivos PDF individuales y cargas masivas comprimidas (`.zip`).
   - Pipeline de limpieza léxica, desguionización multilínea y reconocimiento óptico de caracteres local (Tesseract/Poppler) con respaldo opcional de visión artificial.
3. **Auditoría de Opacidad**:
   - Detección algorítmica de fragmentos con lenguaje potencialmente ambiguo, vago o disuasorio.
   - Flujo de revisión forense y registro de bitácora de hallazgos.
4. **Análisis Comparativo de Vocabulario**:
   - **Contraste Micro (Venn)**: Coincidencias y divergencias entre un reporte corporativo y una lista pericial experta.
   - **Evolución Interanual**: Contraste longitudinal entre reportes de la misma empresa (términos omitidos, persistentes y emergentes).
   - **Acoplamiento Macro (Co-Inercia)**: Análisis multivariante de matrices documentales mediante el **Coeficiente RV de Escoufier**, test de significancia estadística Monte Carlo y proyección visual en **Grafo en Estrella (Radial Star Plot)**.
5. **Marcos de Conocimiento y Listas de Expertos**:
   - Gestión de vocabularios técnicos por peritos acreditados y profesiones normalizadas.
6. **Espacios de Trabajo Aislados (Multi-tenant)**:
   - Separación estricta de datos, expedientes y permisos por equipo o área de auditoría.
7. **Internacionalización y Accesibilidad**:
   - Soporte bilingüe completo (`es` / `en`) y sistema de diseño adaptativo con soporte para modo claro y oscuro.

---

## 👥 Roles de Usuario y Permisos

- **Administrador**: Control total del sistema, configuración de espacios de trabajo, gestión de usuarios, catálogos y auditoría global.
- **Auditor**: Gestión de entidades corporativas, subida de expedientes, análisis de opacidad, conteos léxicos y comparativas multivariantes.
- **Experto / Perito**: Rol especializado enfocado en el registro y mantenimiento de marcos de vocabulario técnico de contraste.

---

## 🛠️ Requisitos Previos

- **Python** 3.12 o 3.13
- **Dependencias del Sistema**:
  - `poppler-utils` (renderizado y conversión de PDFs a imagen)
  - `tesseract-ocr` + paquete de idioma español (`tessdata/spa`)
  - `gettext` (compilación de traducciones internacionales)

Consulta la guía detallada de instalación en [docs/setup/dependencies.md](docs/setup/dependencies.md).

---

## ⚡ Instalación y Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone <URL_DEL_REPOSITORIO> ComplexIndexV2
cd ComplexIndexV2
```

### 2. Configurar el entorno virtual de Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Copia la plantilla `.env.example` y define las variables locales:
```bash
cp .env.example .env
```
*(Para detalles de configuración de API keys opcionales, consulta [docs/setup/api_keys.md](docs/setup/api_keys.md)).*

### 4. Migraciones de Base de Datos y Compilación de Idiomas
```bash
python manage.py migrate
python manage.py compilemessages -l en
```

### 5. Crear usuario administrador
```bash
python manage.py createsuperuser
```

### 6. Iniciar el servidor de desarrollo
```bash
python manage.py runserver
```
Accede a la plataforma desde tu navegador en: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 📂 Comandos de Gestión y Mantenimiento

El sistema incluye comandos Django CLI para administración y saneamiento de datos:

### 1. Importar catálogo base de empresas
Puebla un espacio de trabajo con el dataset corporativo oficial (442 empresas ecuatorianas):
```bash
python manage.py import_companies --workspace <ID_ESPACIO>
```
*(Utiliza por defecto `Counter/resources/Empresas.xlsx`, o puedes especificar un archivo personalizado con `--file /ruta/archivo.xlsx`).*

### 2. Reprocesar reportes con el nuevo motor lingüístico
Recalcula métricas de complejidad, legibilidad INFLESZ y sincroniza palabras en expedientes existentes:
```bash
python manage.py reprocess_reports --workspace-id <ID_ESPACIO>
```
*(Opcionalmente agrega `--from-file` para re-analizar el archivo PDF físico en disco).*

### 3. Depuración de reportes duplicados
Elimina expedientes duplicados por espacio, empresa y año, preservando el que posea mayor cantidad de texto procesado:
```bash
# Simular sin aplicar cambios:
python manage.py clean_duplicate_reports --dry-run

# Ejecutar limpieza real:
python manage.py clean_duplicate_reports
```

### 4. Saneamiento léxico de conteos
Depura ruido OCR residual y palabras fusionadas, sincronizando las tablas analíticas:
```bash
python manage.py purge_invalid_words --workspace-id <ID_ESPACIO>
```

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con una suite integral de 94 pruebas unitarias y de integración que validan el pipeline léxico, la seguridad de autenticación, el aislamiento multitenant, los filtros de opacidad y el motor matemático de Co-Inercia:

```bash
python manage.py test Counter User
```

---

## 📁 Arquitectura del Repositorio

```text
ComplexIndexV2/
├── Counter/                   # Aplicación principal de auditoría y análisis léxico
│   ├── management/commands/   # Comandos CLI (importación, reprocesamiento, saneamiento)
│   ├── resources/             # Datasets base (diccionario_es.txt, Empresas.xlsx)
│   ├── static/                # CSS (Tailwind/Shell), JS interactivo e iconos
│   ├── templates/             # Plantillas Django con diseño ELI
│   ├── coinertia.py           # Motor de Co-Inercia multivariante y Coeficiente RV
│   ├── cleaner.py             # Pipeline de depuración, stopwords y lematización
│   ├── utils.py               # Fórmulas de legibilidad (INFLESZ) y métricas
│   └── views/                 # Controladores organizados por dominio
├── User/                      # Autenticación, perfiles periciales y permisos
├── WordCounter/               # Configuración central del framework Django
├── locale/                    # Catálogos de internacionalización (ES / EN)
├── docs/                      # Documentación técnica organizada
│   ├── CHANGELOG.md           # Registro formal de versiones y fases
│   ├── architecture/          # Especificaciones de diseño, métricas y OCR
│   ├── setup/                 # Guías de instalación de dependencias y APIs
│   └── audits/                # Informes históricos de auditoría técnica
├── manage.py
└── requirements.txt           # Dependencias de producción
```

---

## ❓ Preguntas Frecuentes y Solución de Problemas

### Error: `No module named django`
El entorno virtual no está activo. Ejecuta `source .venv/bin/activate` (o activa tu entorno correspondiente) antes de correr comandos `manage.py`.

### Error: `pdftoppm: command not found` o fallo en OCR
Faltan las dependencias de sistema. Revisa [docs/setup/dependencies.md](docs/setup/dependencies.md) e instala `poppler-utils` y `tesseract-ocr`.

### Las traducciones no se reflejan en inglés
Asegúrate de haber compilado los catálogos gettext con:
```bash
python manage.py compilemessages -l en
```

---

## 📄 Documentación Adicional

- [Sistema de Diseño ELI](docs/architecture/design_system.md)
- [Especificación de Métricas e Índices de Complejidad](docs/architecture/metrics_specification.md)
- [Pipeline de Extracción y OCR](docs/architecture/ocr_implementation.md)
- [Registro de Versiones y Fases (Changelog)](docs/CHANGELOG.md)
