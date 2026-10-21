document.addEventListener("DOMContentLoaded", () => {
    const yearSelect = document.getElementById("id_year");
    const reportSelect = document.getElementById("id_report");

    if (!yearSelect || !reportSelect) return;

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
                console.error("Error al cargar reportes:", error);
                reportSelect.innerHTML = '<option value="">Error al cargar</option>';
            });
    });

    // ==========================================
    // Diagrama de Venn: enfocar una región
    // ==========================================
    const regionTriggers = document.querySelectorAll("[data-compare-region]");
    const detailCards = document.querySelectorAll(".compare-detail");
    const clearFocusButton = document.getElementById("clearVennFocus");

    if (!regionTriggers.length || !detailCards.length) return;

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

    regionTriggers.forEach(trigger => {
        trigger.addEventListener("click", () => toggleRegion(trigger));

        trigger.addEventListener("keydown", event => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            toggleRegion(trigger);
        });
    });

    if (clearFocusButton) {
        clearFocusButton.addEventListener("click", () => setActiveRegion(null));
    }
});
