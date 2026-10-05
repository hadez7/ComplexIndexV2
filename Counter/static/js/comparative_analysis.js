document.addEventListener("DOMContentLoaded", () => {
    const yearSelect = document.getElementById("id_year");
    const reportSelect = document.getElementById("id_report");

    if (!yearSelect || !reportSelect) return;

    yearSelect.addEventListener("change", function () {
        const year = this.value;

        reportSelect.innerHTML = '<option value="">Loading reports...</option>';

        if (!year) {
            reportSelect.innerHTML = '<option value="">Select a report</option>';
            return;
        }

        fetch(`/reports-by-year/?year=${encodeURIComponent(year)}`)
            .then(response => response.json())
            .then(data => {
                reportSelect.innerHTML = '<option value="">Select a report</option>';

                if (data.length === 0) {
                    reportSelect.innerHTML = '<option value="">No reports for this year</option>';
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
                console.error("Error loading reports:", error);
                reportSelect.innerHTML = '<option value="">Error loading</option>';
            });
    });
});
