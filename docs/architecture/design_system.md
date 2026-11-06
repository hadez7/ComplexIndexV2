# Sistema de Diseño ELI (Enterprise Lex Index)

Este documento especifica la arquitectura de interfaz de usuario, tokens de diseño, componentes base y lineamientos visuales de la plataforma **ELI**.

---

## 1. Principios de Diseño

1. **Claridad Analítica**: Interfaces densas en información pero con jerarquías tipográficas y espaciales que facilitan la auditoría pericial y lectura ejecutiva.
2. **Tokens Centralizados**: Colores, superficies y contrastes gobernados por variables CSS (`:root` y `.dark`) sin duplicación de clases utilitarias de modo oscuro.
3. **Internacionalización Nativa**: Soporte bilingüe (`es` / `en`) con strings traducibles (`{% trans %}`) y longitud de texto flexible.
4. **Respeto a la Lógica de Negocio Django**: Modificaciones estrictamente desacopladas de modelos, señales y contextos de vista.

---

## 2. Tokens de Color y Superficie

Definidos en `Counter/static/css/input.css` y consumidos en `Counter/static/css/shell.css`:

| Token | Propósito (Tema Claro) | Propósito (Tema Oscuro) |
|---|---|---|
| `--canvas` | Fondo principal de la aplicación (`#f8fafc`) | Fondo profundo del shell (`#0b0f19`) |
| `--surface` | Paneles, tarjetas y contenedores (`#ffffff`) | Superficie elevada (`#111827`) |
| `--surface-hover` | Estado hover de tarjetas y filas (`#f1f5f9`) | Estado hover (`#1e293b`) |
| `--ink` | Texto principal de alta legibilidad (`#0f172a`) | Texto principal blanco suave (`#f8fafc`) |
| `--muted` | Texto secundario y etiquetas (`#475569`) | Texto secundario atenuado (`#94a3b8`) |
| `--faint` | Texto terciario, placeholders y bordes tenues (`#94a3b8`) | Atenuado terciario (`#64748b`) |
| `--line` | Separadores y bordes estructurales (`#e2e8f0`) | Separadores en modo oscuro (`#1e293b`) |
| `--line-strong` | Bordes activos y divisores resaltados (`#cbd5e1`) | Bordes resaltados (`#334155`) |
| `--blue` | Color primario de marca y acciones principales (`#2563eb`) | Azul institucional (`#3b82f6`) |
| `--blue-soft` | Fondos de badges primarios e iluminación suave (`#eff6ff`) | Resplandor azul translúcido (`#1e3a8a33`) |
| `--teal` | Indicadores de alta concordancia / éxito (`#0d9488`) | Verde azulado accesible (`#14b8a6`) |
| `--amber` | Advertencias y alertas léxicas moderadas (`#d97706`) | Ámbar accesible (`#f59e0b`) |
| `--red` | Opacidad crítica y rupturas normativas (`#dc2626`) | Rojo accesible (`#ef4444`) |

---

## 3. Tipografía

- **Sans-Serif Principal**: `Manrope` / `Inter`, con escala tipográfica normalizada:
  - Títulos H1: `28px` a `32px` (`tracking: -0.04em`, `font-weight: 700`)
  - Subtítulos / Eyebrow: `10px` (`tracking: 0.12em`, `uppercase`, `font-weight: 700`)
  - Métricas numéricas: `24px` a `30px` (`font-mono`, `tabular-nums`, `font-bold`)
  - Párrafos descriptivos: `12px` a `13px` (`line-height: 1.5`)
- **Monospace**: `JetBrains Mono` / `IBM Plex Mono` para RUCs, porcentajes, métricas de Co-Inercia y hashes.

---

## 4. Componentes Base

- `.primary-action`: Botón de acción principal con elevación suave, foco accesible (`focus-visible`) y altura unificada de 42px (46px en pantallas de autenticación).
- `.secondary-action`: Botón secundario con borde sutil para navegación y acciones auxiliares.
- `.eyebrow` / `.blue-eyebrow`: Indicador de sección en mayúsculas compacto con micro-espaciado.
- `.metric-badge`: Pastillas semánticas de estado (`low`, `medium`, `high`, `pending`).
- `.filter-strip`: Contenedor estilizado para campos de búsqueda y selectores en toolbars de filtro.
- `.compare-stat`: Tarjetas interactivas de contraste numérico con soporte de foco y teclado.

---

## 5. Visualizaciones Interactivas

1. **Diagramas de Venn SVG**: Contraste bidireccional entre vocabularios de reportes y marcos de expertos o evolución interanual de la misma empresa.
2. **Grafo en Estrella de Co-Inercia (Radial Star Plot)**:
   - Proyección polar de distancias euclidianas $d = \sqrt{2(1 - RV)}$ entre el año pivote y los periodos históricos.
   - Órbitas métricas concéntricas con umbrales forenses predefinidos ($d \le 0.55$, $0.85$, $1.10$).
   - Conmutación multivariante entre Matriz General, Matriz Experto y Grafo Dual.
   - Ficha lateral dinámica para inspección forense de vértices al vuelo.

