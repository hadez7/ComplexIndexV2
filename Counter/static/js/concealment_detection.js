document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // Total de ocurrencias
    // ==========================================

    const checks = document.querySelectorAll(".parrafo-check");
    const totalSpan = document.getElementById("total-ocurrencias");

    function recalcular() {

        if (!totalSpan) {
            return;
        }

        let total = 0;

        checks.forEach(check => {

            if (check.checked) {
                total += parseInt(check.dataset.count);
            }

        });

        totalSpan.textContent = total;
    }

    checks.forEach(check => {
        check.addEventListener("change", recalcular);
    });

    recalcular();

    // ==========================================
    // Selects dinámicos
    // ==========================================
    const yearSelect = document.getElementById("year");
    const reportSelect = document.getElementById("report");
    const origen = document.getElementById("origen-palabras");
    const listaExperto = document.getElementById("lista-experto");
    const contenedorLista = document.getElementById("contenedor-lista-experto");
    const palabraSelect = document.getElementById("palabra");

    if (!reportSelect || !origen || !palabraSelect) {
        return;
    }

    const listasElement =
        document.getElementById("expert-lists-data");

    const listas = listasElement
        ? JSON.parse(listasElement.textContent)
        : [];

    const palabraActual =
        palabraSelect.dataset.selected || "";

    // ==========================================
    // Mostrar / ocultar lista experto
    // ==========================================

    function actualizarVisibilidad() {

        if (origen.value === "experto") {

            if (contenedorLista) {
                contenedorLista.style.display = "block";
            }

        } else {

            if (contenedorLista) {
                contenedorLista.style.display = "none";
            }

        }

    }

    // ==========================================
    // Cargar palabras del reporte
    // ==========================================

    function cargarPalabrasReporte(reportId) {

        if (!reportId) {

            palabraSelect.innerHTML =
                '<option value="">Seleccione un reporte</option>';

            return;
        }

        palabraSelect.innerHTML =
            '<option value="">Cargando...</option>';

        fetch(
            `/concealment_detection/ajax/report-words/?report_id=${reportId}`
        )
        .then(response => {

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}`
                );
            }

            return response.json();

        })
        .then(data => {

            palabraSelect.innerHTML = "";

            if (!data || data.length === 0) {

                palabraSelect.innerHTML =
                    '<option value="">Sin palabras disponibles</option>';

                return;
            }

            let seleccionada = false;

            data.forEach(word => {

                const option =
                    document.createElement("option");

                option.value = word;
                option.textContent = word;

                if (
                    palabraActual &&
                    word === palabraActual
                ) {
                    option.selected = true;
                    seleccionada = true;
                }

                palabraSelect.appendChild(option);

            });

            if (
                !seleccionada &&
                palabraSelect.options.length > 0
            ) {
                palabraSelect.selectedIndex = 0;
            }

        })
        .catch(error => {

            console.error(
                "Error cargando palabras:",
                error
            );

            palabraSelect.innerHTML =
                '<option value="">Error al cargar</option>';

        });

    }

    function cargarReportes(year) {

        if (!year) {
            reportSelect.innerHTML =
                '<option value="">Seleccione un año</option>';
            return;
        }

        fetch(
            `/concealment_detection/ajax/reports-by-year/?year=${year}`
        )
        .then(response => {

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}`
                );
            }

            return response.json();

        })
        .then(data => {

            reportSelect.innerHTML = "";

            if (!data || data.length === 0) {

                reportSelect.innerHTML =
                    '<option value="">Sin reportes</option>';

                palabraSelect.innerHTML =
                    '<option value="">Sin palabras disponibles</option>';

                return;
            }

            const selectedId = reportSelect.dataset.selected || "";
            let encontrada = false;

            data.forEach(report => {
                const option = document.createElement("option");
                option.value = report.id;
                option.textContent = report.name;

                if (selectedId && String(report.id) === String(selectedId)) {
                    option.selected = true;
                    encontrada = true;
                }

                reportSelect.appendChild(option);
            });

            if (!encontrada && reportSelect.options.length > 0) {
                reportSelect.selectedIndex = 0;
            }
            reportSelect.dataset.selected = reportSelect.value;

            if (origen.value === "reporte") {

                cargarPalabrasReporte(
                    reportSelect.value
                );

            }

        })
        .catch(error => {

            console.error(
                "Error cargando reportes:",
                error
            );

        });

    }

    // ==========================================
    // Cambio de reporte
    // ==========================================

    reportSelect.addEventListener(
        "change",
        function () {

            this.dataset.selected = this.value;

            if (
                origen.value === "reporte"
            ) {

                cargarPalabrasReporte(
                    this.value
                );

            }

        }
    );

    // ==========================================
    // Cambio de palabra
    // ==========================================

    palabraSelect.addEventListener(
        "change",
        function () {
            this.dataset.selected = this.value;
        }
    );

    // ==========================================
    // Cambio de origen
    // ==========================================

    origen.addEventListener(
        "change",
        function () {

            actualizarVisibilidad();

            if (
                this.value === "experto"
            ) {

                palabraSelect.innerHTML =
                    '<option value="">Seleccione una palabra</option>';

            } else {

                cargarPalabrasReporte(
                    reportSelect.value
                );

            }

        }
    );

    // ==========================================
    // Cambio de lista experto
    // ==========================================

    if (listaExperto) {

        listaExperto.addEventListener(
            "change",
            function () {

                palabraSelect.innerHTML = "";

                const lista = listas.find(
                    item =>
                        item.id == this.value
                );

                if (!lista) {

                    palabraSelect.innerHTML =
                        '<option value="">Seleccione una lista</option>';

                    return;
                }

                if (
                    !lista.words ||
                    lista.words.length === 0
                ) {

                    palabraSelect.innerHTML =
                        '<option value="">Lista vacía</option>';

                    return;
                }

                let seleccionada = false;

                lista.words.forEach(word => {

                    const option =
                        document.createElement("option");

                    option.value = word;
                    option.textContent = word;

                    if (
                        palabraActual &&
                        word === palabraActual
                    ) {
                        option.selected = true;
                        seleccionada = true;
                    }

                    palabraSelect.appendChild(option);

                });

                if (
                    !seleccionada &&
                    palabraSelect.options.length > 0
                ) {
                    palabraSelect.selectedIndex = 0;
                }

            }
        );

    }

    // ==========================================
    // Inicialización
    // ==========================================

    actualizarVisibilidad();

    if (reportSelect.dataset.selected) {
        reportSelect.value = reportSelect.dataset.selected;
    }

    if (
        origen.value === "reporte" &&
        reportSelect.value &&
        (!palabraSelect || palabraSelect.options.length <= 1)
    ) {
        cargarPalabrasReporte(
            reportSelect.value
        );
    }

    if (
        origen.value === "experto" &&
        listaExperto &&
        listaExperto.value
    ) {

        listaExperto.dispatchEvent(
            new Event("change")
        );

    }

    if (
        yearSelect &&
        yearSelect.value &&
        reportSelect.options.length === 0
    ) {
        cargarReportes(
            yearSelect.value
        );
    }
    
    if (yearSelect) {

        yearSelect.addEventListener(
            "change",
            function () {

                reportSelect.dataset.selected = "";
                cargarReportes(
                    this.value
                );

            }
        );

    }

});