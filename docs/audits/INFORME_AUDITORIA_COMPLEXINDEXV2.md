# Informe de Auditoría — ComplexIndexV2 (ELI – Enterprise Lex Index)

**Fecha:** 15 de octubre de 2026
**Proyecto auditado:** `/home/hadez/Projects/ComplexIndexV2`
**Stack:** Django 5.2.1 · Python 3.13.16 · PyMuPDF · Tesseract OCR · OpenAI Vision (respaldo) · SQLite · Tailwind (CDN/local)
**Alcance:** módulos `Counter` y `User`, procesamiento de palabras, seguridad, navegación/UX, integridad de datos y funcionalidades documentadas en `README.md`.
**Naturaleza de este documento:** auditoría de solo lectura. **No se modificó ningún archivo del proyecto**; este informe es el único entregable.

---

## 0. Resumen ejecutivo

El proyecto es funcional y tiene una arquitectura razonablemente organizada (separación de vistas por dominio en `Counter/views/`, aislamiento por `Workspace`, pipeline de limpieza léxica propio en `Counter/cleaner.py`). Sin embargo, presenta **fallos críticos en el corazón del sistema (el procesamiento de palabras)**, en **seguridad** y en **integridad de datos**, además de varias funciones documentadas que no existen.

### Hallazgos más graves

| # | Severidad | Hallazgo | Dónde |
|---|-----------|----------|-------|
| A2 | 🔴 Crítica | Las métricas de complejidad **no usan el pipeline de limpieza**: cuentan basura OCR y stopwords. `Report.total_words` diverge de la tabla real de palabras. | `Counter/utils.py:233,325` |
| A1 | 🔴 Crítica | Falsos negativos: palabras válidas como **`adscripción`** son rechazadas (`adscripcion` → `[]`). | `Counter/cleaner.py:15,155` |
| A3 | 🔴 Crítica | Normalización inconsistente (tildes): las listas de expertos no coinciden con las palabras normalizadas → palabras técnicas mal contadas y análisis comparativo erróneo. | `Counter/utils.py:335`, `general_views.py:355` |
| B2 | 🔴 Crítica | `@csrf_exempt` en creación/edición de empresas → vulnerable a CSRF. | `Counter/views/company_views.py:70,120` |
| B3 | 🔴 Crítica | Borrado/edición sin validar método HTTP ni rol; `update_report` puede asignar una empresa de **otro** espacio de trabajo. | `report_views.py`, `company_views.py`, `expert_list_views.py` |
| B1 | 🔴 Crítica | `SECRET_KEY` hardcodeada, `DEBUG=True`, `ALLOWED_HOSTS=["*"]`. | `WordCounter/settings.py:25,28,30` |
| B4 | 🟠 Alta | **2.627 PDFs reales de empresas** versionados en git (datos confidenciales). | `media/reportes/` |
| D1 | 🟠 Alta | El comando `recalculate_report_metrics` documentado en el README **no existe**. | `README.md:396,402` |
| C1 | 🟠 Alta | **Doble DELETE** de listas de expertos → siempre muestra un error falso. | `expert_lists.html:460` + `expert_lists.js:190` |
| A5 | 🟠 Alta | Conteo de sílabas/INFLESZ impreciso con hiatos (`día`, `país` → 1 sílaba). | `Counter/utils.py:185` |

> **Conclusión clave pedida por el usuario:** hoy el sistema **no garantiza** que no aparezcan palabras incompletas o basura. El pipeline `extraer_palabras_limpias` sí filtra `aaaab`, pero el **conteo de métricas y de palabras técnicas no lo usa**, y el corrector léxico deja pasar/falsea palabras por listas incompletas y por falta de normalización. Ver Sección A.

---

## 1. Metodología

- Lectura completa de `Counter/` (modelos, vistas, formularios, `main.py`, `utils.py`, `cleaner.py`, `stopwords.py`, `middleware.py`, `signals.py`, comandos de management), `User/` y `WordCounter/`.
- **Ejecución real del pipeline** con el entorno del proyecto (`.venv/bin/python`, Django 5.2.1) para reproducir fallos concretos.
- Verificación de rutas URL registradas y nombres duplicados ejecutando el resolver de Django.
- Revisión de plantillas y JS (`Counter/static/js/*.js`, `Counter/templates/*.html`).
- Contraste con la documentación (`README.md`, `INDICE_COMPLEJIDAD.md`, `IMPLEMENTATION_GPT5_MINI.md`, `CONFIGURAR_API_KEY.md`).

Evidencia de pruebas reproducibles al final (Anexo).

---

## A. Procesamiento de palabras (corazón del sistema)

Esta es la parte prioritaria. El pipeline real vive en `Counter/cleaner.py` y se invoca desde `Counter/main.py:count_words()` → `extraer_palabras_limpias()`. Ese pipeline **sí** está bien encaminado, pero: (1) no lo usan todas las rutas, (2) contiene listas incompletas que generan falsos negativos, y (3) no hay corrección ortográfica real.

### A1 — Falsos negativos: palabras válidas rechazadas por listas incompletas 🔴

**Cómo falla**
`es_palabra_valida_espanol()` (`Counter/cleaner.py:114`) descarta cualquier secuencia de 4+ consonantes que no esté en la lista cerrada `CONSONANTES_VALIDAS_4 = {'nstr','nscr','rstr','bstr','dstr','pstr','ntr','ndr','mpr','mpl'}` (línea 15, rama línea 155–158). La lista es **incompleta**: faltan grupos legítimos del español como `dscr` (ad**scr**ipción), `bscr` (su**bscr**ibir), `scr`, `str` en posiciones no iniciales, etc.

Además, la lista mezcla grupos de **3** letras (`ntr`, `ndr`, `mpr`, `mpl`) que **nunca** se consultan, porque la rama solo evalúa `len(grupo) == 4`. Es código muerto que revela la intención original (`ntr` en *encuentro*, `mpl` en *ejemplo*) pero que no valida nada.

**Caso de ejemplo (reproducido)**
```text
extraer_palabras_limpias("adscripcion", STOPWORDS)  ->  []          # ❌ RECHAZADA
```
`adscripción` es una palabra legítima del español (contratos: "adscripción laboral"). El sistema la descarta silenciosamente y **pierde** la palabra del conteo, del `TotalCountReport` y de las búsquedas. En documentos jurídicos/financieros esto elimina terminología clave.

Otros falsos negativos del mismo tipo que se producirán: `subscripcion`, `subscribir`, `adsorber` (cluster `dsr` de 3 no aplica), `circunscripcion` (contiene `nscr`, pero cualquier variante con `scr` inicial tras consonante fallará).

**Solución a implementar**
1. **Sustituir la allowlist cerrada por un diccionario real.** Cargar una lista de palabras del español (p. ej. la lista de ~600.000 formas de `pyspellchecker`/`hunspell-es`, o el paquete `spacy` con modelo `es_core_news_*`) y validar con ella, usando la heurística fonotáctica solo como respaldo cuando la palabra no esté en el diccionario.
2. Como parche inmediato, completar la lista con todos los grupos válidos y **eliminar los grupos de 3** de `CONSONANTES_VALIDAS_4` (o moverlos a una constante aparte y usarlos en una rama `len(grupo) == 3`):
   ```python
   CONSONANTES_VALIDAS_4 = {'nstr','nscr','rstr','bstr','dstr','pstr','scr','str',
                            'dscr','bscr','nscr','lstr','cstr','gstr'}
   ```
3. Añadir tests de regresión con un corpus de palabras jurídicas (`adscripción`, `subscripción`, `circunscripción`, `prescripción`, `inscripción`, `obscuro`, `abstracto`).

---

### A2 — Las métricas de complejidad NO usan el pipeline de limpieza 🔴 (el fallo más grave)

**Cómo falla**
Existen **dos caminos** para contar palabras y son incompatibles:

| Camino | Cómo cuenta | Limpieza |
|--------|-------------|----------|
| Tabla de palabras (`TotalCountReport`) | `main.count_words()` → `extraer_palabras_limpias()` | ✅ limpia (dedup, fonotáctica, stopwords) |
| Métricas del `Report` (`total_words`, `unique_words`, sílabas, INFLESZ) | `utils.calcular_metricas_complejidad()` usa `re.findall(r'\b[a-záéíóúüñ]+\b', texto)` | ❌ **ninguna** |
| Palabras técnicas | `utils.contar_palabras_tecnicas()` usa `re.findall(...)` directo | ❌ **ninguna** |

`calcular_metricas_complejidad` (`Counter/utils.py:233`) y `contar_palabras_tecnicas` (`Counter/utils.py:325`) **nunca** importan ni llaman a `cleaner`. Por tanto cuentan:
- basura OCR (`aaaab`, tokens pegados que el regex no separa igual),
- **stopwords** (`de`, `la`, `que`, `y`…), que el conteo real sí elimina,
- números romanos y fragmentos que el pipeline descarta.

**Caso de ejemplo**
Un PDF escaneado donde el usuario **ve** en la tabla 4.180 palabras "reales", pero `Report.total_words = 5.306` porque el conteo de métricas incluyó stopwords y ruido. Consecuencias directas y visibles:
- El "Total de Palabras" del Índice de Complejidad y la suma de la tabla **no cuadran**. Cualquier auditor que sume la tabla y compare con la tarjeta de complejidad detecta la inconsistencia.
- `unique_words / total_words` (diversidad léxica) se diluye con stopwords repetidas → **diversidad subestimada**.
- `contar_palabras_tecnicas` puede dar >0 o contar coincidencias espurias por fragmentos.

**Solución a implementar**
1. **Unificar la fuente de verdad.** Que `calcular_metricas_complejidad` use el mismo pipeline que el conteo:
   ```python
   from .cleaner import extraer_palabras_limpias
   def calcular_metricas_complejidad(texto, stopwords_normalizadas):
       palabras = extraer_palabras_limpias(texto, stopwords_normalizadas)
       total_words = len(palabras)
       unique_words = len(set(palabras))
       ...
   ```
   `main.py:24` ya construye `STOPWORDS_ES_NORMALIZADAS`; hay que pasarlo a `calcular_metricas_complejidad` y a `contar_palabras_tecnicas`.
2. Hacer que `contar_palabras_tecnicas` reciba las palabras **ya extraídas** (evitar re-tokenizar y aplicar el mismo pipeline).
3. Añadir una **prueba de invariante**: `report.total_words == TotalCountReport.filter(report=report).aggregate(Sum('quantity'))` para todo reporte procesado.

---

### A3 — Normalización inconsistente de palabras (tildes y mayúsculas) 🔴

**Cómo falla**
Hay tres normalizaciones distintas conviviendo:

| Lugar | Normalización aplicada |
|-------|------------------------|
| Palabras guardadas en `TotalCountReport` (pipeline) | `.lower()` + `.strip()` + **`quitar_tildes()`** |
| `ExpertWord.words` (lo que el usuario escribe) | **se guarda tal cual** |
| Comparación en `comparative_analysis_view.normalize_words()` | solo `.strip().lower()` → **sin quitar tildes** |
| `contar_palabras_tecnicas()` | `str(palabra_tecnica).lower()` → **sin quitar tildes** |

El pipeline normaliza el texto del documento **sin tildes**, pero las listas de expertos y las comparaciones conservan las tildes. **Las palabras acentuadas nunca coinciden.**

**Caso de ejemplo**
- La lista del experto contiene `["gestión", "auditoría", "razón"]`.
- El documento (ya normalizado) produce las palabras `["gestion", "auditoria", "razon"]`.
- `contar_palabras_tecnicas` compara `"gestión"` contra `{"gestion", ...}` → **no coincide** → `technical_words_count = 0` aunque el documento esté lleno de esos términos. → **Densidad técnica = 0**, complejidad general distorsionada.
- En el **Análisis Comparativo**, `"gestion"` aparece en "solo documento" y `"gestión"` en "solo lista", cuando son **la misma palabra**. El informe de comparación es engañoso.

**Solución a implementar**
1. **Normalizar en el punto de entrada** a las listas de expertos: cuando se guardan/leen `ExpertWord.words`, aplicar la **misma** función de normalización del pipeline (`quitar_tildes(w.lower().strip())`). Idealmente en `ExpertWord.save()` o en `create_list`/`update_list`.
2. Actualizar `normalize_words()` y `contar_palabras_tecnicas()` para usar `quitar_tildes`:
   ```python
   from .cleaner import quitar_tildes
   def normalize_words(word_list):
       return {quitar_tildes(w.strip().lower()) for w in word_list if w}
   ```
3. Migración de datos para normalizar las listas **ya existentes** (`purge_invalid_words` puede extenderse para esto).

---

### A4 — `Report.total_words` diverge de `TotalCountReport` (integridad de datos) 🔴

**Cómo falla**
Consecuencia combinada de A2 y de que existen **dos orígenes de conteo** que nunca se reconcilian. Además:
- `recalcular_metricas_reporte()` (`Counter/utils.py:421`) recalcula métricas sobre un texto **modificado manualmente** (quitando ocurrencias de palabras "descartadas" en la Detección de Opacidad) usando la regex cruda, no el pipeline → la divergencia **crece** tras cada revisión de opacidad.
- Al borrar un reporte (`report_views.delete_report`) se sincroniza `TotalCount` con `sincronizar_palabras_total_count`, pero **nunca** se recalcula ningún agregado de métricas.

**Caso de ejemplo**
Un reporte con `Report.total_words = 5.306`; la suma real de `TotalCountReport.quantity` es 4.180. El "Índice de Complejidad" promedia ambos mundos: las tarjetas de métricas usan 5.306 y la tabla de palabras muestra 4.180. No existe ningún comando ni botón que reconcilie estos valores.

**Solución a implementar**
1. Aplicar A2 (una sola fuente de conteo).
2. Crear el comando `recalculate_report_metrics` (ver D1) y una tarea/botón que lo exponga.
3. Añadir una prueba de integridad permanente (ver A2 punto 3).

---

### A5 — Conteo de sílabas / INFLESZ impreciso (hiatos) 🟠

**Cómo falla**
`contar_silabas_palabra()` (`Counter/utils.py:185`) cuenta **grupos vocálicos consecutivos** como una sola sílaba, tratando todo como diptongo. No detecta **hiatos** (vocal tónica cerrada + abierta, o dos abiertas).

**Caso de ejemplo (reproducido)**
```text
contar_silabas_palabra("dia")   -> 1   # correcto: 2 (dí-a)
contar_silabas_palabra("pais")  -> 1   # correcto: 2 (pa-ís)
contar_silabas_palabra("rio")   -> 1   # correcto: 2 (rí-o)
contar_silabas_palabra("tia")   -> 1   # correcto: 2 (tí-a)
```
Como `total_syllables` alimenta el **INFLESZ** (`(total_syllables/total_words)*100`), y el INFLESZ alimenta `inverted_inflesz` → `inflesz_score` → **Complejidad General**, el subconteo de sílabas **sesga sistemáticamente** los índices de legibilidad y complejidad a la baja.

**Solución a implementar**
- Implementar reglas de hiato (o usar una librería: `pyphen` con locale `es`, o un silabeador específico). Reglas mínimas:
  - vocal abierta (`a e o`) + vocal cerrada (`i u`) tónica → **hiato** (2 sílabas): `día`, `país`, `río`, `tía`.
  - dos vocales abiertas → hiato: `aé` en `a-é-re-o`.
  - `ü` (`güe`, `güi`) es diptongo; `qu`/`gu` no cuentan la `u`.
- Añadir tests con palabras con hiato y diptongo (`ciudad`=2, `aire`=2, `día`=2, `cuidado`=3).

---

### A6 — `ARTEFACTOS_RECURRENTES` es un parche manual no generalizable 🟡

**Cómo falla**
`Counter/cleaner.py:30` corrige artefactos OCR con un **diccionario fijo** (`'compaiiia'→'compañia'`, `'admlnlstraclon'→'administracion'`, etc.). Funciona solo para los casos ya vistos. Cualquier nuevo artefacto (`'adm1nistracion'`, `'admlnlstracion'`, `'represenlante'`, `'con1paiiia'`) pasa sin corregir.

**Caso de ejemplo (reproducido)**
```text
"compaiiia"        -> ['compañia']          # ✅ está en la lista
"admlnlstraclon"   -> ['administracion']    # ✅ está en la lista
"represenlanle"    -> ['representante']     # ✅ está en la lista
"adm1nistracion"   -> []                    # ❌ no está: se pierde
"represenlante"    -> ['represenlante']     # ❌ variante no cubierta → basura que pasa
```
Es decir, el sistema **sí produce palabras "basura"** (como pide el usuario que no ocurra) en cuanto el OCR genera una variante no listada.

**Solución a implementar**
1. Reemplazar el parche por **corrección por similitud**: para cada token no reconocido, buscar la palabra más cercana en un diccionario del español usando distancia de edición (Levenshtein / `fuzzywuzzy` — **ya está en `requirements.txt`**) o `rapidfuzz`, y sustituir solo si la similitud supera un umbral (p. ej. ≥ 85) **y** la palabra candidata existe en el diccionario.
2. Mantener `ARTEFACTOS_RECURRENTES` como *caché* de correcciones ya validadas, no como única defensa.
3. Encender este corrector con un flag para no alterar nombres propios/RUCs.

---

### A7 — Validación aislada permite basura si no se pasa por el pipeline 🟡

**Cómo falla**
`es_palabra_valida_espanol("aaaab")` devuelve **`True`** de forma aislada (`Counter/cleaner.py:114`): la función no rechaza letras repetidas por sí misma; eso lo hace `corregir_caracteres_repetidos` **antes** de llamarla (en `procesar_palabra_individual`). Es decir, la defensa es **posicional**: si cualquier código futuro llama directamente a `es_palabra_valida_espanol`, basura como `aaaab` pasa.

**Caso de ejemplo (reproducido)**
```text
es_palabra_valida_espanol("aaaab", STOPWORDS)  ->  True   # ❌
corregir_caracteres_repetidos("aaaab")          ->  "ab"  # y "ab" < 3 → se descarta por longitud
```
El resultado final `extraer_palabras_limpias("aaaab")` sí da `[]`, pero por una cadena de efectos frágil.

**Solución a implementar**
- Mover la regla de "mismo carácter repetido 3+ veces de forma anómala" **dentro** de `es_palabra_valida_espanol` (además de la reducción), de modo que la función sea **auto-contenida** y no dependa del orden de llamadas.
- Añadir la comprobación `if re.search(r'(.)\1{2,}', word): return False` para letras fuera de `LETRAS_DOBLES_VALIDAS`.

---

## B. Seguridad

### B1 — Configuración de producción insegura (crítica) 🔴

**Cómo falla** — `WordCounter/settings.py`:
```python
SECRET_KEY = 'django-insecure-^gk1(7ojfy_j^h!f&n-pdf+xn56lsqq^)-8rqhbxyupz^z-%@_'  # línea 25
DEBUG = True                                                                        # línea 28
ALLOWED_HOSTS = ["*"]                                                               # línea 30
```
No hay `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_*`, `SECURE_CONTENT_TYPE_NOSNIFF`.

**Caso de ejemplo**
Con `DEBUG=True`, cualquier error 500 muestra **el código fuente, rutas y variables de entorno** (potencialmente `OPENAI_API_KEY`) al navegador. Con `SECRET_KEY` pública, un atacante puede **falsificar cookies de sesión** y autenticarse como cualquier usuario (incluido admin). `ALLOWED_HOSTS=["*"]` permite *Host header attacks*.

**Solución**
```python
import os
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]        # obligatorio en prod
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
# Seguridad (solo prod):
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```
Rotar la `SECRET_KEY` actual y sacarla del control de versiones. Ejecutar `python manage.py check --deploy`.

---

### B2 — `@csrf_exempt` en creación/edición de empresas 🔴

**Cómo falla** — `Counter/views/company_views.py:70-71` y `:120-121` desactivan la protección CSRF:
```python
@login_required
@csrf_exempt
def create_company(request): ...
@login_required
@csrf_exempt
def update_company(request, company_id): ...
```
El frontend **ya envía** el token (`Counter/static/js/companies.js:50,141,172` usan `X-CSRFToken`), por lo que `@csrf_exempt` es innecesario y solo abre la puerta.

**Caso de ejemplo**
Un usuario autenticado visita `sitio-malicioso.com`, que incluye un `<form action="https://eli/companies/create/" method="post">`. Como el endpoint no exige CSRF, el navegador envía la cookie de sesión y **se crea una empresa arbitraria** en el espacio de trabajo de la víctima. Con `update_company` el atacante puede **renombrar/cambiar RUC y provincia** de empresas existentes.

**Solución**
- Eliminar `@csrf_exempt` de **ambas** vistas (el JS ya manda el token). Añadir `@require_POST`/`@require_http_methods(["POST"])`.
- Test: comprobar que un POST sin token devuelve `403`.

---

### B3 — Endpoints sin control de método ni de rol; fuga entre espacios de trabajo 🔴

**Cómo falla**

| Vista | Problema |
|-------|----------|
| `report_views.delete_report` (`:100`) | No valida método: un **GET** borra el reporte (y su PDF). Sin rol. |
| `report_views.update_report` (`:118`) | Sin método; y **`Company.objects.get(id=company_id)` no filtra por `workspace`** (`:128`) → **IDOR**: se puede reasignar el reporte a una empresa de **otro** espacio de trabajo. |
| `company_views.delete_company` (`:113`) | Sin método; borra sin comprobar existencia ni rol. |
| `expert_list_views.create_list / update_list / delete_list / create_expert` | Solo `@login_required`: **cualquier** usuario (rol auditor/viewer) puede crear/editar/borrar listas de vocabulario y expertos. `create_expert` hace `User.objects.get(id=user_id)` sin validar ámbito. |

**Caso de ejemplo**
1. Un usuario con rol *Lector* abre una imagen cuyo `src` es `/expert_lists/12/delete/` (o el navegador precarga un enlace) → la lista se borra (el endpoint acepta POST pero nada impide invocarlo desde un contexto no autorizado; solo falta el check de rol).
2. Un auditor del Espacio A obtiene el `company_id` de una empresa del Espacio B (o adivina) y hace `POST /reports/55/update/ {"company": <id_B>}` → el reporte del Espacio A queda **vinculado a una empresa del Espacio B**, rompiendo el aislamiento que el resto del código protege cuidadosamente.

**Solución**
1. Añadir `@require_POST` a **todas** las mutaciones (`delete_report`, `update_report`, `delete_company`, `update_company`, `create_list`, `update_list`, `delete_list`, `create_expert`).
2. Decorar con verificación de rol/membresía (p. ej. `@user_passes_test(lambda u: u.is_staff or es_admin_de_workspace(u, ws))`).
3. **Filtrar toda FK por `workspace`**: `Company.objects.get(id=company_id, workspace=current_ws)`.
4. Tests de IDOR: intentar operar sobre IDs de otro workspace debe dar `403/404`.

---

### B4 — Datos confidenciales versionados en git 🟠

**Cómo falla**
Hay **2.627 PDFs reales de empresas** trackeados en el repositorio:
```text
media/reportes/16CORPORACION_CELESTE_S._A._CORPACEL.pdf
media/reportes/16FISA_FUNDICIONES_INDUSTRIALES_SA.pdf
... (2.627 archivos)
media/zip_uploads/DOLMEN.zip, DOLTREX.zip, DREAMPACK.zip
```
`.gitignore` **no** excluye `media/` ni `*.pdf`. `db.sqlite3` sí está ignorado (bien) y `.env` también (bien).

**Caso de ejemplo**
Al clonar el repo (o si se publica en GitHub), cualquiera obtiene **todos los reportes financieros confidenciales** de las empresas auditadas. Es una fuga de datos de negocio, no solo de código.

**Solución**
1. Añadir a `.gitignore`: `media/reportes/`, `media/zip_uploads/`.
2. **Sacar** los PDFs del índice de git sin borrarlos del disco:
   ```bash
   git rm -r --cached media/reportes media/zip_uploads
   ```
3. Si el repo ya se compartió, **purgar el historial** (`git filter-repo --path media/ --invert-paths`) y rotar cualquier credencial expuesta. Adjuntar los PDFs por otro canal (almacenamiento local, S3 privado).

---

### B5 — Documento binario `.mo` trackeado pese a estar ignorado 🟡

**Cómo falla**
`locale/en/LC_MESSAGES/django.mo` está en el repositorio aunque `.gitignore` incluye `*.mo` (la regla no aplica a archivos ya rastreados).

**Caso de ejemplo**
Cada cambio de traducción regenera el `.mo` y produce diffs binarios ruidosos / conflictos de merge.

**Solución**
```bash
git rm --cached locale/en/LC_MESSAGES/django.mo
```
y conseguir que los `.mo` se generen en build (`compilemessages`).

---

### B6 — XSS almacenado vía `innerHTML` 🟠

**Cómo falla**
Se construye HTML por concatenación e se inyecta con `innerHTML` usando datos que provienen de campos **de texto libre** (nombre de archivo PDF, nombre de empresa, RUC, username):
- `Counter/templates/totalcount.html:584` (`data.words.map(item => ...)`) y la tabla de complejidad (`report_name`, `company_name`).
- `Counter/templates/concealment_history.html:320-325`.
- `Counter/static/js/users.js:394-417` (`data.logs.map(...)`).
- `Counter/static/js/companies.js:71-84`.

**Caso de ejemplo**
Se sube un PDF llamado `<img src=x onerror=fetch('/expert_lists/1/delete/',{method:'POST'})>.pdf` (o se registra una empresa con ese nombre). Al abrir la tabla de palabras / el historial, el HTML se inyecta y el `onerror` **se ejecuta** en el navegador de cualquier usuario (incluido admin) → XSS con capacidad de realizar acciones autenticadas.

**Solución**
- Usar `textContent`/`createElement` en lugar de `innerHTML`, o escapar los valores (función `escapeHtml`) antes de interpolarlos.
- Añadir una **Content-Security-Policy** restrictiva y `X-Content-Type-Options: nosniff` (ver B1).

---

## C. Navegación y UX (frontend)

### C1 — Doble DELETE en listas de expertos → error falso siempre 🟠

**Cómo falla**
El botón de confirmación tiene **dos** manejadores para el mismo clic:
- `expert_lists.html:460`: `onclick="confirmDeleteListAction()"` (función inline, `:499`).
- `expert_lists.js:190`: `confirmDeleteBtn?.addEventListener('click', ...)`.

Al hacer clic se disparan **dos** `fetch` de borrado (`expert_lists.html:506` y `expert_lists.js:194`).

**Caso de ejemplo**
El usuario elimina una lista: la primera petición borra (`success:true`), la segunda recibe **404** porque la lista ya no existe → `data.success` es falsy → se ejecuta `alert('No se pudo eliminar la lista.')` (`expert_lists.js:210`). El usuario ve **un error aunque el borrado fue correcto**, y puede reintentar pensando que falló.

**Solución**
- Definir el manejador **una sola vez**. Eliminar el `onclick` inline (`expert_lists.html:460`) y dejar el listener del JS externo, o viceversa; y borrar la función duplicada.
- Añadir guardas de idempotencia (deshabilitar el botón mientras la petición está en vuelo).

---

### C2 — Nombres de URL duplicados (`totalcount`, `export_excel`) 🟠

**Cómo falla**
Verificado con el resolver de Django:
```text
totalcount    -> ['totalcount/', 'reports/total_count/']
export_excel  -> ['totalcount/export_excel/', 'reports/total_count/export_excel/']
```
El origen: `Counter/urls.py:23` incluye `path("totalcount/", include("Counter.other.urls_total_count"))` **y** `Counter/other/urls_report.py` vuelve a incluir `path("total_count/", include("Counter.other.urls_total_count"))`.

**Caso de ejemplo**
`{% url 'totalcount' %}` puede resolverse a `reports/total_count/` (la **última** definición gana) en lugar de `totalcount/`. Cualquier enlace generado por nombre puede apuntar a una ruta no deseada, desincronizando el `data-path` de resaltado activo del sidebar (el JS compara `data-path` con `location.pathname`).

**Solución**
- Eliminar el `include` redundante en `Counter/other/urls_report.py` (la línea `path("total_count/", include("Counter.other.urls_total_count"))`).
- Añadir un test que verifique que `reverse('totalcount') == '/totalcount/'` y que no hay nombres duplicados.

---

### C3 — Funciones inalcanzables desde la navegación principal 🟡

**Cómo falla**
- **Historial de Opacidad** (`concealment_history`) no está en el sidebar ni en el drawer; solo se llega por un enlace dentro de `concealment_detection.html` (`:32`, `:270`). El usuario no descubre la funcionalidad.
- La **gestión de miembros** de espacio (`workspace_members`) solo es accesible desde `workspaces_list`, no desde el menú de trabajo.

**Caso de ejemplo**
Un auditor no encuentra cómo revisar el historial de validaciones de opacidad porque no hay entrada de menú; cree que la función no existe.

**Solución**
- Añadir entradas al sidebar y al drawer móvil: "Historial de Opacidad" (`concealment_history`), y "Miembros" cuando haya un espacio activo.
- Resaltar el item activo usando el mismo patrón `data-path`.

---

### C4 — Errores de red silenciados en `fetch` 🟡

**Cómo falla**
`Counter/static/js/companies.js` y `Counter/static/js/reports.js` encadenan `.then(...)` **sin `.catch`** en varias rutas (`companies.js:96,114,144,175`; `reports.js:31,69,81,113`). Si falla la red o el servidor responde error no-JSON, la promesa se rechaza sin feedback.

**Caso de ejemplo**
Al eliminar una empresa con el backend caído, el botón queda en estado "cargando" y **no aparece ningún mensaje**; el usuario no sabe si se borró o no.

**Solución**
- Añadir `.catch(err => { console.error(err); mostrarToast('Error de conexión, reintente.'); })` en todas las cadenas.
- Un helper `fetchJson()` centralizado que maneje errores y CSRF.

---

### C5 — Código muerto / endpoint sin uso 🟡

**Cómo falla**
`Counter/static/js/users.js:11` declara `expert: '/users/.../expert/'` (endpoint `users_assign_expert`) que no se usa en ese archivo; y quedan funciones/valores duplicados (`openDeleteListModal`/`closeDeleteListModal` definidos en HTML y en JS).

**Solución**
- Eliminar el endpoint sin uso o documentarlo; consolidar las funciones duplicadas (ver C1).

---

## D. Funciones documentadas / esperadas que faltan

### D1 — El comando `recalculate_report_metrics` no existe 🟠

**Cómo falla**
`README.md:393-403` documenta:
```bash
python manage.py recalculate_report_metrics --solo-faltantes
python manage.py recalculate_report_metrics --dry-run
```
Pero `Counter/management/commands/` **solo** contiene: `clean_duplicate_reports.py`, `import_companies.py`, `purge_invalid_words.py`.

**Caso de ejemplo**
```text
$ python manage.py recalculate_report_metrics --solo-faltantes
Unknown command: 'recalculate_report_metrics'
```
El operador no puede reparar métricas, justo la operación que haría falta por A2/A4.

**Solución**
Crear `Counter/management/commands/recalculate_report_metrics.py`:
```python
from django.core.management.base import BaseCommand
from Counter.models import Report
from Counter.utils import recalcular_metricas_reporte
from Counter.main import sincronizar_palabras_total_count

class Command(BaseCommand):
    help = "Recalcula métricas de complejidad de los reportes."
    def add_arguments(self, parser):
        parser.add_argument("--solo-faltantes", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
    def handle(self, *args, **opts):
        qs = Report.objects.all()
        if opts["solo_faltantes"]:
            qs = qs.filter(total_words__isnull=True)
        for r in qs.iterator():
            if opts["dry_run"]:
                self.stdout.write(f"[dry-run] {r.id} {r.name}"); continue
            recalcular_metricas_reporte(r)
            sincronizar_palabras_total_count(
                r.totalcountreport_set.values_list("word", flat=True),
                workspace=r.workspace)
        self.stdout.write(self.style.SUCCESS("Métricas recalculadas."))
```
(Y, una vez aplicada A2, usar el pipeline limpio dentro de `recalcular_metricas_reporte`.)

---

### D2 — Exportación de complejidad a Excel no implementada 🟡

**Cómo falla**
`README.md:262-265` lista "Exportación de Complejidad a Excel" como mejora pendiente; solo existe `totalcount/export_excel/` (que exporta la tabla de palabras). El botón de exportar (`totalcount.html:93`) ignora la pestaña de complejidad.

**Solución**
- Añadir `export_complexity_excel` que exporte `get_complexity_metrics()` con las 8 métricas, y un botón en la pestaña correspondiente. (O, si no se va a implementar, ajustar el README.)

---

### D3 — `YEAR_CHOICES` fijo a 2016–2025 (falta 2026) 🟠

**Cómo falla**
`Counter/forms.py:7-9`:
```python
YEAR_CHOICES = [("", _("Detección automática desde el documento"))] + \
               [(str(y), str(y)) for y in range(2025, 2015, -1)]
```
En 2026 el desplegable de "Año del Reporte" **no ofrece 2026**.

**Caso de ejemplo**
Un analista sube un informe de 2026; no puede seleccionar el año en el formulario y queda forzado a la autodetección (que puede fallar) o a editar después.

**Solución**
```python
from django.utils import timezone
YEAR_CHOICES = [("", _("Detección automática desde el documento"))] + \
               [(str(y), str(y)) for y in range(timezone.now().year, 2015, -1)]
```

---

### D4 — Traducción incompleta / archivos de idioma dispersos 🟡

**Cómo falla**
Hay `.po/.mo` en `locale/` pero también `messages.mo` suelto en la raíz del proyecto, y `messages.mo` no se regenera con `compilemessages` correctamente ubicado. Riesgo de traducciones desincronizadas.

**Solución**
- Centralizar todo en `locale/`, eliminar `messages.mo` de la raíz, documentar `django-admin compilemessages` en el README.

---

## E. Rendimiento

### E1 — Cálculo de complejidad en memoria sobre TODOS los reportes 🔴

**Cómo falla**
El endpoint AJAX de complejidad llama `get_complexity_metrics(request)` **sin `limit`** (`Counter/views/total_count_views.py:236`). Esa función (`:65`) recorre **todos** los `Report` del workspace y calcula métricas **campo a campo en Python** en cada petición, sin caché. Con miles de reportes (el proyecto ya tiene cientos de PDFs) cada clic en "Complejidad" recorre todo.

**Caso de ejemplo**
Con 2.000 reportes, cada cambio de filtro/orden dispara ~2.000 iteraciones y un `Paginator` en memoria; el usuario percibe latencia de varios segundos.

**Solución**
- Paginar/ordenar **en base de datos** (anotar `diversity`, `technical_density` con `annotate`) y no traer todo a Python.
- Aplicar `limit`/`offset` en la llamada AJAX igual que el SSR (`offset=0, limit=25`).
- Cachear agregados por (workspace, filtros).

---

### E2 — Consultas costosas en el conteo y en la importación 🟡

**Cómo falla**
- `get_filtered_total_counts` filtra con `word__icontains` (`:158`) → *full scan* sin índice.
- `insertar_empresas` (`utils.py:388`) hace `exists()` **fila por fila** al importar el Excel (N+1).
- `concealment_detection_view` recalcula `find_paragraph` con regex por párrafo en cada POST.

**Solución**
- Índices en `word`, `report(year)`, `company(ruc)`; usar `annotate`+`Count` en lugar de iterar.
- En la importación, precargar RUCs existentes en un `set` y hacer `bulk_create`.
- Cachear/precomputar los párrafos de una palabra.

---

### E3 — Coste de OCR/OpenAI sin límites 🟡

**Cómo falla**
Cada PDF escaneado puede disparar OCR Tesseract y, si falla, llamadas a `gpt-4o-mini` **por página** (`utils.py:86`). No hay límite de uso ni cola.

**Solución**
- Añadir throttling/cola (Celery/RQ) y límites por usuario; registrar consumo; validar que las imágenes sean legibles antes de gastar API.

---

## F. Tabla resumen priorizada

| Prioridad | ID | Título | Archivo principal |
|-----------|----|--------|-------------------|
| P0 | A2 | Métricas no usan pipeline limpio (divergencia de conteos) | `Counter/utils.py` |
| P0 | A1 | Falsos negativos (`adscripcion`) | `Counter/cleaner.py` |
| P0 | A3 | Normalización inconsistente de tildes | `Counter/utils.py`, `general_views.py` |
| P0 | B1 | `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` inseguros | `WordCounter/settings.py` |
| P0 | B2 | `@csrf_exempt` en empresas | `company_views.py` |
| P0 | B3 | Sin método/rol + IDOR en `update_report` | `report_views.py`, etc. |
| P1 | B4 | PDFs confidenciales en git | `media/reportes/` |
| P1 | D1 | Comando `recalculate_report_metrics` inexistente | `Counter/management/commands/` |
| P1 | C1 | Doble DELETE en listas de expertos | `expert_lists.html`/`.js` |
| P1 | A5 | Sílabas/INFLESZ imprecisos (hiatos) | `Counter/utils.py` |
| P1 | A4 | `total_words` diverge de la tabla | `Counter/utils.py` |
| P1 | B6 | XSS vía `innerHTML` | plantillas y JS |
| P1 | D3 | `YEAR_CHOICES` sin 2026 | `Counter/forms.py` |
| P2 | C2 | URLs duplicadas (`totalcount`, `export_excel`) | `urls.py` |
| P2 | E1 | Complejidad en memoria sobre todos los reportes | `total_count_views.py` |
| P2 | A6 | `ARTEFACTOS_RECURRENTES` no generaliza | `Counter/cleaner.py` |
| P2 | A7 | Validación léxica no autocontenida | `Counter/cleaner.py` |
| P2 | C3 | Historial de opacidad fuera del menú | `base.html` |
| P2 | C4 | Errores `fetch` silenciados | `companies.js`/`reports.js` |
| P3 | B5 | `.mo` trackeado | `locale/en/.../django.mo` |
| P3 | D2 | Exportación de complejidad pendiente | `total_count_views.py` |
| P3 | D4 | Traducciones dispersas | `locale/`, raíz |
| P3 | E2/E3 | Rendimiento importación/OCR | `utils.py` |
| P3 | C5 | Código muerto | `users.js` |

---

## Anexo — Evidencia de pruebas reproducibles

Ejecutado con `.venv/bin/python` (Django 5.2.1, Python 3.13.16).

### Pipeline de palabras
```text
PALABRA            EXTRAIDA
abitacion          ['abitacion']        # ❌ no se corrige a "habitacion"
aaaab              []                   # ✅ rechazada (vía reducción + longitud)
aaab               []                   # ✅ rechazada
adscripcion        []                   # ❌ FALSO NEGATIVO
compaiiia          ['compañia']         # ✅ (por lista manual)
admlnlstraclon     ['administracion']   # ✅ (por lista manual)
represenlanle      ['representante']    # ✅ (por lista manual)
construccion       ['construccion']     # ✅
inscripcion        ['inscripcion']      # ✅
abstraccion        ['abstraccion']      # ✅

es_palabra_valida_espanol('aaaab') = True       # ❌ aisladamente
corregir_caracteres_repetidos('aaaab') = 'ab'
CONSONANTES_VALIDAS_4 (len 3, nunca usados) = ['mpl','mpr','ndr','ntr']
```

### Sílabas (INFLESZ)
```text
dia   -> 1   (debería 2)
pais  -> 1   (debería 2)
rio   -> 1   (debería 2)
tia   -> 1   (debería 2)
accion-> 2   (ok)   habitacion -> 4 (ok)   realidad -> 3 (ok)
```

### Fórmula de complejidad general (discrepancia README vs. código)
```text
calcular_complejidad_general(0.5, 0.3, 0.2)  = 0.333   # código: (div + leg + dens)/3
README esperaría (0.5 + (1-0.3) + 0.2)/3      = 0.467   # (div + (1-leg) + dens)/3
```
> `Counter/utils.py:382` usa `(diversidad + legibilidad + densidad)/3`, pero el docstring (`:364`) y el README (`:56`) dicen `(Diversidad + (1 - Legibilidad) + Densidad)/3`. Además `get_complexity_metrics` llama al parámetro `readability_index` cuando en realidad es `inverted_inflesz` (complejidad, no legibilidad). **Corregir la fórmula y el nombre del parámetro** (`technical_density`/`legibilidad` mezclados).

### Rutas URL duplicadas (resolver de Django)
```text
totalcount    -> ['totalcount/', 'reports/total_count/']
export_excel  -> ['totalcount/export_excel/', 'reports/total_count/export_excel/']
```

### Configuración y datos
```text
SECRET_KEY = 'django-insecure-...'   DEBUG = True   ALLOWED_HOSTS = ["*"]
PDFs trackeados en git: 2627   (media/reportes/ y media/zip_uploads/)
.gitignore: no excluye media/ ni *.pdf;  locale/en/LC_MESSAGES/django.mo trackeado
Comandos existentes: clean_duplicate_reports, import_companies, purge_invalid_words
(recalculate_report_metrics NO existe)
```

---

## Anexo — Plan de corrección recomendado (orden sugerido)

1. **Seguridad mínima para cualquier despliegue:** B1, B2, B3, B4.
2. **Corazón del sistema:** A2 (unificar conteo) → A1 (diccionario) → A3 (normalización) → A5 (sílabas) → A6/A7 (corrector y validación).
3. **Integridad y mantenimiento:** D1 (comando), A4 (invariante/tests), D3 (años).
4. **UX/navegación:** C1 (doble delete), C2 (URLs), B6 (XSS), C3/C4.
5. **Rendimiento:** E1, E2, E3.

> Este informe no ha modificado ningún archivo del proyecto. Todos los cambios aquí descritos son propuestas para que el equipo las implemente y valide con pruebas.
