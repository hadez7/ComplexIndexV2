document.addEventListener("DOMContentLoaded", () => {

    const yearSelect = document.getElementById("id_year");
    const reportSelect = document.getElementById("id_report");

    if (!yearSelect || !reportSelect) return;

    yearSelect.addEventListener("change", function () {

        const year = this.value;

        reportSelect.innerHTML =
            '<option value="">Cargando...</option>';

        fetch(`/reports-by-year/?year=${year}`)
            .then(response => response.json())
            .then(data => {

                reportSelect.innerHTML =
                    '<option value="">Seleccione un reporte</option>';

                data.forEach(report => {

                    const option =
                        document.createElement("option");

                    option.value = report.id;
                    option.textContent = report.name;

                    reportSelect.appendChild(option);

                });

            })
            .catch(error => {

                console.error(error);

                reportSelect.innerHTML =
                    '<option value="">Error al cargar</option>';

            });

    });

});