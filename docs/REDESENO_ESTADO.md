# Estado del rediseño ELI — documento de traspaso

> **Fecha:** 2026-10-21 · **Rama:** `rediseno-eli` · **Commit puntero:** `9a57d53`
> **Origen del diseño:** Figma "ELI / Enterprise Lex Index".
> Este documento existe para continuar el trabajo desde otra máquina (migración a Fedora)
> sin pérdida de contexto. Leerlo antes de tocar nada.

---

## 1. Objetivo del proyecto

Rediseño progresivo de ComplexIndexV2 según el diseño ELI, **preservando TODO el
comportamiento de Django**: contextos de plantilla, nombres de campos, CSRF, `next`,
URLs, backend y flujos funcionales (autenticación, subida PDF/ZIP, detección de
duplicados, reportes, espacios de trabajo, expertos). El rediseño es **estético**:
si algo no se puede tocar sin alterar comportamiento, no se toca.

## 2. Cómo continuar (checklist en Fedora)

```bash
# 1. Recuperar el código (bundle por USB o git clone si se sube a GitHub)
git clone /ruta/ComplexIndexV2-migracion-fedora.bundle ComplexIndexV2
cd ComplexIndexV2 && git checkout rediseno-eli

# 2. Entorno Python (se recrea; NO copiar el .venv de Arch)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Dependencias del sistema (Fedora)
#    git, python3, nodejs+npm, gettext (compilemessages), poppler-utils, tesseract-ocr
#    (ver INSTALACION_POPPLER.md en la raíz)

# 4. Front-end
npm install
npm run build:css

# 5. Datos que NO van en git (copiar a mano desde la máquina vieja)
#    - db.sqlite3   (60 MB; en el worktree viejo era un symlink al checkout principal)
#    - .env         (SECRET_KEY y API keys)

# 6. Traducciones compiladas (.mo no se versiona)
python manage.py compilemessages -l en

# 7. Verificación
python manage.py test Counter User   # → 85 tests OK
python manage.py check               # → limpio
```

**Versiones con las que se trabajó:** Python 3.13.16, Node v26.12.0, npm 11.20.0.
En Fedora no hace falta `.venv` heredado ni `node_modules` (ambos ignorados por git).

**Para que OpenCode continúe el hilo:** abrir `opencode` en la raíz del repo y pedirle
que lea `docs/REDESENO_ESTADO.md` (este archivo). La conversación anterior vive en la
BD local de OpenCode de la máquina vieja (`~/.local/share/opencode/opencode.db`) y no
tiene exportación oficial.

## 3. Convenciones del rediseño (NO romper)

- **Tokens ELI** en `Counter/static/css/input.css` (`:root` y `.dark`): `--canvas`,
  `--surface`, `--surface-hover`, `--ink`, `--muted`, `--faint`, `--line`,
  `--line-strong`, `--blue`, `--blue-deep`, `--blue-soft`, `--cyan`, `--violet`,
  `--violet-soft`, `--teal`, `--teal-soft`, `--amber`, `--amber-soft`, `--red`,
  `--red-soft`, `--indigo`, `--indigo-soft`, `--pink`, `--pink-soft`, `--header`.
  Usar variables en plantillas; **no** añadir clases `dark:` nuevas (el modo oscuro se
  resuelve por herencia de tokens y por `shell.css`).
- **Componentes base** (input.css): `.eyebrow`, `.blue-eyebrow`, `.primary-action`,
  `.secondary-action`, `.company-card`, `.status-pill`, `.landing-hero`, `.logo-orbit`,
  `.auth-*`. Reutilizarlos antes de inventar estilos nuevos.
- **Tailwind v3**: si se añaden clases arbitrarias nuevas en plantillas, ejecutar
  `npm run build:css` y subir la versión de caché `?v=eli-XX` en
  `WordCounter/templates/base.html` y `User/templates/base_auth.html` (tailwind.min.css).
  `shell.css` (eli-19) y `shell.js`/`custom_select.js` (eli-17) tienen versión propia.
  Ojo: `.hidden` no oculta `.primary-action` (el CSS crudo va después de las utilidades);
  para ocultar CTAs usar `hidden` solo donde el componente no fija `display`, o
  `max-sm:!hidden`.
- **Shell**: `base.html` expone `{% block app_shell %}` que envuelve sidebar + canvas.
  La landing pública (`Counter/templates/index.html`) lo reemplaza por su propia carcasa;
  los scripts del shell quedan fuera del bloque.
- **i18n**: todo texto visible envuelto en `{% trans %}`. Los **msgid canónicos** son el
  mismo identificador en todas las páginas (p. ej. `"Panel de Conteo - Análisis de
  Complejidad"`, `"Historial de Ocultamiento de Información"`) — conservarlos o se rompen
  las pruebas de internacionalización. Tras cambiar textos:
  `manage.py makemessages -l en` + traducir + `manage.py compilemessages -l en`.
  ⚠️ El merge puede dejar entradas **fuzzy**, que gettext ignora (renderizan en español):
  revisar con `grep -B4 '^#, fuzzy' locale/en/LC_MESSAGES/django.po` y corregir
  (quitar `#, fuzzy` y `#|` y dejar el `msgstr` correcto).

## 4. Fases completadas (23 commits: `a0e223e` … `9a57d53`)

| Fase | Commit | Contenido |
|---|---|---|
| 0 | `a0e223e` | Tokens ELI, componentes core, tipografía Manrope / IBM Plex Mono |
| 1 | `f5b83e3` | Shell ELI: nav-rail oscuro, logo órbita, header translúcido |
| 2 | `149d99e` | Observatorio (panel.html) |
| 3 | `5ed6e5e` | Autenticación ELI (login y registro) |
| 4 | `4314fdd` | Ingesta documental (upload) |
| 4.5 | `8189afe` | Colores semánticos y aislamiento del tema oscuro legacy |
| 5 | `73a2cae` | Expedientes (reports.html) |
| 6 | `d646ef1` | Directorio de empresas |
| 7 | `2f08d49` | Conteo consolidado y complejidad |
| 8 | `0ed6ec9` | Detección de ocultamiento e historial |
| 9 | `25cdc10` | Contraste de vocabularios (diagrama de Venn) |
| 10 | `703fc4e` | Vocabularios y listas de expertos |
| 11 | `edab068` + `19c3a7f` | Espacios de trabajo y gestión de usuarios |
| 12 | `6a377cd` | Limpieza del shell, partials y CSS/JS externos |
| 13 | `6b4a0df` | Landing pública (primera versión ELI) |
| 14 | `61c7d7e` | Perfil de usuario |
| 15 | `f03b3c3` | Detalle de conteo por reporte |
| fix | `795bfce` | Textos canónicos e i18n (85 tests en verde) |
| 16 | `9a57d53` | Landing pública dedicada + sidebar sin "Inicio" |

## 5. Cambios de producto de la Fase 16 (última)

- **Landing pública dedicada** (página previa a login/registro, sin barra lateral de
  app): barra superior propia con marca, anclas (El programa / Cómo funciona / Módulos /
  Para quién), selector ES/EN, tema claro-oscuro y CTA de acceso. Secciones: hero,
  El programa, Cómo funciona (3 pasos), Módulos (6 tarjetas), Para quién, CTA final y
  pie público. Verificada en claro, oscuro, móvil (390 px) e inglés.
- **Sidebar autenticada**: eliminado el ítem "Inicio" (modos admin y experto); la entrada
  del panel ahora se llama **"Observatorio"** (en inglés: **"Dashboard"**); el logo del
  shell lleva a Observatorio para usuarios autenticados no expertos; breadcrumbs con
  destino al panel renombrados en 9 plantillas + perfil; en espacios de trabajo el
  breadcrumb distingue experto ("Inicio") y resto ("Observatorio"); CTA de la tarjeta de
  espacio activo: "Entrar al Observatorio".
- **Tests**: `Counter/tests.py` (líneas ≈287, 405, 420, 434) actualizados al nuevo rótulo.
- **i18n**: 41 traducciones nuevas (landing + "Observatorio"→"Dashboard") y 18 entradas
  fuzzy corregidas. `msgfmt --check` OK.

## 6. Estado de verificación (2026-10-21)

- `python manage.py test Counter User` → **85 tests OK**
- `python manage.py check` → sin incidencias
- `git diff --check` → limpio (árbol limpio en `9a57d53`)
- Capturas revisadas (Brave headless): landing anónima claro/oscuro/móvil/inglés,
  landing autenticada ES/EN, panel admin (sin "Inicio", con "Observatorio"), sidebar de
  experto, espacios de trabajo con breadcrumb.

## 7. Pendientes conocidos

1. **i18n completa (EN)**: quedan **447 msgids** sin traducir de 793 activos
   (225 fuzzy + 222 vacíos) — estimación 3–5 h. La landing y los títulos canónicos ya
   están traducidos; el resto son textos de pantallas de la app.
2. **QA end-to-end**: 2–4 h para recorrer auth, subida PDF/ZIP, duplicados, reportes y
   espacios en claro/oscuro/móvil.
3. **Push / PR**: la rama `rediseno-eli` no tiene upstream. Remotes del repo:
   `mine` = `github.com:hadez7/ComplexIndexV2`, `origin` = `github.com/rafaellazo/ComplexIndexV2`.
   La rama `main` local está **1 commit por delante** de `mine/main` sin pushear.
   El usuario prefiere no subir a GitHub aún (por eso existe el bundle).
4. **Detalle menor**: en páginas de peritaje (expert) el breadcrumb "Observatorio" apunta
   al panel, al que el experto no accede (redirección) — comportamiento previo al
   rediseño, no introducido ahora.
5. **Checkout principal** (`/home/hadez/Projects/ComplexIndexV2`, rama `main`) con cambios
   **sin commitear**: `Counter/tests.py`, `Counter/views/general_views.py`,
   `Counter/templates/comparative_analysis.html` y `Counter/coinertia.py` (archivo nuevo).
   Copiarlos o commitearlos antes de dar de baja la máquina.

## 8. Notas de entorno (máquina Arch vieja)

- `ComplexIndexV2-rediseno` es un **worktree** de `../ComplexIndexV2` (las ramas viven en
  el repo principal). No confundir con un clon independiente.
- `.venv` (Python 3.13.16) vive en el checkout principal: `/home/hadez/Projects/ComplexIndexV2/.venv`.
- `db.sqlite3` (60 MB) **no** está versionado; en el worktree era un symlink al principal.
- `.env` (SECRET_KEY y API keys) **no** está versionado.
- `media/` **sí** está versionado: 2627 PDFs, ~805 MB empaquetados → cualquier clon o
  bundle pesa ~800 MB.
- Traducciones: `locale/en/LC_MESSAGES/django.po` está versionado; el `.mo` compilado no.
