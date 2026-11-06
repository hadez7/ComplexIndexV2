# Changelog de Complejidad y Rediseño ELI

Todos los cambios notables, evoluciones arquitectónicas y rediseños de la plataforma **ELI (Enterprise Lex Index)** quedan registrados en este documento.

---

## [Fase 17] - 2026-11-05
### Añadido
- **Módulo de Co-Inercia y Red Multivariante (Grafo en Estrella)**:
  - Integración de `Counter/coinertia.py` con Coeficiente RV de Escoufier y test de significancia estadística Monte Carlo ($p$-valor).
  - Pestaña interactiva en Análisis Comparativo con grafo en estrella SVG, órbitas métricas de distancia euclidiana y panel forense de inspección.
  - Tabla de distancias y similitud por año histórico con badges semánticos de continuidad léxica.
  - 4 pruebas unitarias adicionales en `CoinertiaAnalysisTests` (suite completa en 94/94 tests OK).
- **Estandarización de Alturas y Accesibilidad de Foco**:
  - Unificación de controles de filtrado a 42px en todas las vistas de la aplicación y 46px en pantallas de acceso.
  - Reemplazo de `outline` rectangular tosco del navegador por resplandor de foco suave (`box-shadow: 0 0 0 3px var(--blue-soft)`) con `:focus-within`.
  - Corrección de padding en campos de búsqueda (`padding-left: 36px`) para evitar superposición con iconos SVG.
  - Menú desplegable adaptativo en `upload.html` con altura dinámica calculada y eliminación de recortes por `overflow: hidden`.
- **Estructuración del Repositorio**:
  - Reubicación de dataset semilla `Empresas.xlsx` en `Counter/resources/Empresas.xlsx`.
  - Reorganización modular de la documentación en `docs/setup/`, `docs/architecture/` y `docs/audits/`.
  - Eliminación de archivos temporales y memorándums obsoletos de la raíz.

---

## [Fase 16] - 2026-10-21
### Añadido
- **Landing Pública Dedicada**: Página inicial sin barra lateral con barra de navegación institucional, órbita de telemetría animada, selector ES/EN y selector de tema claro/oscuro.
- Renombrado de navegación de "Inicio" a "Observatorio" (Dashboard en EN) y ajuste de breadcrumbs multitenant.

---

## [Fases 0 a 15] - Resumen del Rediseño ELI
- **Fase 15**: Detalle de conteo léxico individual por reporte.
- **Fase 14**: Perfil de usuario y edición de credenciales.
- **Fase 13**: Primera versión de la landing pública ELI.
- **Fase 12**: Limpieza profunda del shell de aplicación y unificación de partials.
- **Fase 11**: Gestión de espacios de trabajo (*workspaces*) multitenant y administración de usuarios/roles.
- **Fase 10**: Gestión de vocabularios periciales y listas de expertos.
- **Fase 9**: Contraste de vocabularios con diagramas de Venn interactivos.
- **Fase 8**: Detección de patrones lingüísticos de opacidad e historial de auditoría.
- **Fase 7**: Conteo consolidado de frecuencias y métricas de complejidad.
- **Fase 6**: Directorio de entidades corporativas y filtrado por RUC/provincia.
- **Fase 5**: Registro y gestión de expedientes corporativos (`reports.html`).
- **Fase 4**: Ingesta documental por lotes (ZIP y PDFs individuales con OCR).
- **Fase 3**: Autenticación corporativa (login y registro).
- **Fase 2**: Observatorio ejecutivo con Signal Board analítico.
- **Fase 1**: Shell de navegación lateral oscuro con logo de órbita y header translúcido.
- **Fase 0**: Fundamentos de diseño, tokens CSS y tipografía institucional.

