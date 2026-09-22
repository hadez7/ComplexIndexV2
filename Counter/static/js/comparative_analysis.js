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
});
