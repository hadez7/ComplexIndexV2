document.addEventListener("DOMContentLoaded", () => {
    // ==========================================
    // 1. Selector de año y reporte (Pestaña 1: Experto)
    // ==========================================
    const yearSelect = document.getElementById("id_year");
    const reportSelect = document.getElementById("id_report");

    if (yearSelect && reportSelect) {
        yearSelect.addEventListener("change", function () {
            const year = this.value;

            reportSelect.innerHTML = '<option value="">Cargando reportes...</option>';

            if (!year) {
                reportSelect.innerHTML = '<option value="">Seleccione un reporte</option>';
                return;
            }

            fetch(`/reports-by-year/?year=${encodeURIComponent(year)}`)
                .then(response => response.json())
                .then(data => {
                    reportSelect.innerHTML = '<option value="">Seleccione un reporte</option>';

                    if (data.length === 0) {
                        reportSelect.innerHTML = '<option value="">No hay reportes para este año</option>';
                        return;
                    }

                    data.forEach(report => {
                        const option = document.createElement("option");
                        option.value = report.id;
                        option.textContent = report.name;
                        reportSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error("Error al cargar reportes por año:", error);
                    reportSelect.innerHTML = '<option value="">Error al cargar</option>';
                });
        });
    }

    // ==========================================
    // 2. Selector de empresa y reportes (Pestaña 2: Interanual)
    // ==========================================
    const companySelect = document.getElementById("interanual_company");
    const reportASelect = document.getElementById("interanual_report_a");
    const reportBSelect = document.getElementById("interanual_report_b");

    function loadReportsForCompany(companyId) {
        if (!reportASelect || !reportBSelect) return;

        reportASelect.innerHTML = '<option value="">Cargando reportes...</option>';
        reportBSelect.innerHTML = '<option value="">Cargando reportes...</option>';

        if (!companyId) {
            reportASelect.innerHTML = '<option value="">Seleccione un reporte...</option>';
            reportBSelect.innerHTML = '<option value="">Seleccione un reporte...</option>';
            return;
        }

        fetch(`/reports-by-company/?company_id=${encodeURIComponent(companyId)}`)
            .then(response => response.json())
            .then(data => {
                reportASelect.innerHTML = '<option value="">Seleccione un reporte...</option>';
                reportBSelect.innerHTML = '<option value="">Seleccione un reporte...</option>';

                if (data.length === 0) {
                    reportASelect.innerHTML = '<option value="">Sin reportes para esta empresa</option>';
                    reportBSelect.innerHTML = '<option value="">Sin reportes para esta empresa</option>';
                    return;
                }

                data.forEach(report => {
                    const optA = document.createElement("option");
                    optA.value = report.id;
                    optA.textContent = report.name;
                    reportASelect.appendChild(optA);

                    const optB = document.createElement("option");
                    optB.value = report.id;
                    optB.textContent = report.name;
                    reportBSelect.appendChild(optB);
                });

                // Si hay 2 o más reportes, preseleccionar report_a (año anterior) y report_b (año más reciente)
                // Los datos vienen ordenados descendente por año (-year), p. ej. [2025, 2024, ...]
                if (data.length >= 2) {
                    reportBSelect.selectedIndex = 1; // 2025 (más reciente)
                    reportASelect.selectedIndex = 2; // 2024 (anterior)
                } else if (data.length === 1) {
                    reportASelect.selectedIndex = 1;
                    reportBSelect.selectedIndex = 1;
                }

                // Disparar evento change por si componentes externos o custom selects están observando
                reportASelect.dispatchEvent(new Event("change", { bubbles: true }));
                reportBSelect.dispatchEvent(new Event("change", { bubbles: true }));
            })
            .catch(error => {
                console.error("Error al cargar reportes de la empresa:", error);
                reportASelect.innerHTML = '<option value="">Error al cargar</option>';
                reportBSelect.innerHTML = '<option value="">Error al cargar</option>';
            });
    }

    if (companySelect && reportASelect && reportBSelect) {
        companySelect.addEventListener("change", function () {
            loadReportsForCompany(this.value);
        });

        // Si ya hay una empresa seleccionada al cargar la página pero los selectores de reportes están vacíos
        if (companySelect.value && reportASelect.options.length <= 1) {
            loadReportsForCompany(companySelect.value);
        }
    }

    // ==========================================
    // 3. Conmutador de Pestañas (Modo Experto vs Interanual)
    // ==========================================
    const tabBtnExperto = document.getElementById("tabBtnExperto");
    const tabBtnInteranual = document.getElementById("tabBtnInteranual");
    const tabContentExperto = document.getElementById("tabContentExperto");
    const tabContentInteranual = document.getElementById("tabContentInteranual");

    function switchTab(mode) {
        if (!tabContentExperto || !tabContentInteranual) return;

        const isInteranual = mode === "interanual";

        tabContentExperto.classList.toggle("hidden", isInteranual);
        tabContentInteranual.classList.toggle("hidden", !isInteranual);

        if (tabBtnExperto && tabBtnInteranual) {
            tabBtnExperto.classList.toggle("border-[var(--blue)]", !isInteranual);
            tabBtnExperto.classList.toggle("text-[var(--blue)]", !isInteranual);
            tabBtnExperto.classList.toggle("border-transparent", isInteranual);
            tabBtnExperto.classList.toggle("text-[var(--muted)]", isInteranual);

            tabBtnInteranual.classList.toggle("border-[var(--blue)]", isInteranual);
            tabBtnInteranual.classList.toggle("text-[var(--blue)]", isInteranual);
            tabBtnInteranual.classList.toggle("border-transparent", !isInteranual);
            tabBtnInteranual.classList.toggle("text-[var(--muted)]", !isInteranual);
        }

        try {
            const url = new URL(window.location.href);
            if (isInteranual) {
                url.searchParams.set("modo", "interanual");
            } else {
                url.searchParams.delete("modo");
            }
            window.history.replaceState({}, "", url.toString());
        } catch (e) {}
    }

    if (tabBtnExperto) {
        tabBtnExperto.addEventListener("click", function (e) {
            e.preventDefault();
            switchTab("experto");
        });
    }

    if (tabBtnInteranual) {
        tabBtnInteranual.addEventListener("click", function (e) {
            e.preventDefault();
            switchTab("interanual");
        });
    }

    // ==========================================
    // 4. Tarjetas de métricas: enfocar una región / columna
    // ==========================================
    const regionTriggers = document.querySelectorAll("[data-compare-region]");
    const detailCards = document.querySelectorAll(".compare-detail");
    const clearFocusButton = document.getElementById("clearVennFocus");
    const clearInteranualFocusButton = document.getElementById("clearInteranualFocus");

    function setActiveRegion(region) {
        detailCards.forEach(card => {
            const isActive = card.dataset.region === region;
            card.classList.toggle("is-focused", Boolean(region) && isActive);
            card.classList.toggle("is-dimmed", Boolean(region) && !isActive);
        });

        regionTriggers.forEach(trigger => {
            const isActive = trigger.dataset.compareRegion === region;
            trigger.classList.toggle("is-active", isActive);
            if (trigger.tagName === "BUTTON") {
                trigger.setAttribute("aria-pressed", isActive ? "true" : "false");
            }
        });

        if (clearFocusButton) {
            clearFocusButton.classList.toggle("hidden", !region);
        }
        if (clearInteranualFocusButton) {
            clearInteranualFocusButton.classList.toggle("hidden", !region);
        }

        if (region && window.matchMedia("(max-width: 1023px)").matches) {
            const target = document.querySelector(`.compare-detail[data-region="${region}"]`);
            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        }
    }

    function toggleRegion(trigger) {
        const region = trigger.dataset.compareRegion;
        const isAlreadyActive = trigger.classList.contains("is-active");
        setActiveRegion(isAlreadyActive ? null : region);
    }

    if (regionTriggers.length && detailCards.length) {
        regionTriggers.forEach(trigger => {
            trigger.addEventListener("click", () => toggleRegion(trigger));

            trigger.addEventListener("keydown", event => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                toggleRegion(trigger);
            });
        });
    }

    if (clearFocusButton) {
        clearFocusButton.addEventListener("click", () => setActiveRegion(null));
    }
    if (clearInteranualFocusButton) {
        clearInteranualFocusButton.addEventListener("click", () => setActiveRegion(null));
    }

    // ==========================================
    // 5. Filtrado de términos por columna de desglose
    // ==========================================
    const searchInputs = document.querySelectorAll(".search-region-terms");
    searchInputs.forEach(input => {
        input.addEventListener("input", function () {
            const query = this.value.toLowerCase().trim();
            const card = this.closest(".compare-detail") || document.querySelector(`.compare-detail[data-region="${this.dataset.targetRegion}"]`);
            if (!card) return;

            const chips = card.querySelectorAll(".terms-container .term-chip");
            chips.forEach(chip => {
                const word = (chip.dataset.word || chip.textContent || "").toLowerCase();
                chip.style.display = word.includes(query) ? "" : "none";
            });
        });
    });
});
