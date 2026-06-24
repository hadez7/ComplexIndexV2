// ---------------------------------------- UTILIDADES ----------------------------------------
// Obtiene el valor de una cookie por nombre (para CSRF)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const trimmed = cookie.trim();
            if (trimmed.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(trimmed.slice(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

// Limpia los mensajes de error de los campos del formulario
function clearErrors() {
    ['id', 'name', 'year', ''].forEach(field => {
        const errorEl = document.getElementById('error-' + field);
        if (errorEl) errorEl.innerText = '';
    });
}

// ---------------------------------------- DETALLES ----------------------------------------
// Muestra el modal de detalles de una empresa
function showDetails(id) {
    fetch(`/reports/${id}/json/`)
    .then(response => response.json())
    .then(data => {
        document.getElementById('detail-id').innerText = id;
        document.getElementById('detail-name').innerText = data.name;
        document.getElementById('detail-year').innerText = data.year;
        document.getElementById('detail-company').innerText = data.company.name;
        document.getElementById('detailsModal').classList.remove('hidden');
    });
}

// Cierra el modal de detalles
function closeDetailsModal() {
    document.getElementById('detailsModal').classList.add('hidden');
}

// ---------------------------------------- ELIMINACIÓN ----------------------------------------
let reportToDelete = null;

// Abre el modal de confirmación de borrado
function openDeleteModal(id) {
    reportToDelete = id;
    document.getElementById('deleteModal').classList.remove('hidden');
}

// Cierra el modal de borrado
function closeDeleteModal() {
    reportToDelete = null;
    document.getElementById('deleteModal').classList.add('hidden');
}

// Realiza la petición AJAX para borrar el reporte
function deleteReport() {
    fetch(`/reports/${reportToDelete}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
        }
    })
    .then(response => {
        if (response.ok) {
            document.getElementById(`reporte-${reportToDelete}`).remove();
            closeDeleteModal();
            location.reload();
        }
    });
}

// ---------------------------------------- EDICIÓN ----------------------------------------
// Abre el modal de edición y llena los campos con los datos actuales
function openEditModal(id) {
    fetch(`/reports/${id}/json/`)
    .then(response => response.json())
    .then(data => {
        document.getElementById('edit-id').value = id;
        document.getElementById('edit-name').value = data.name;
        document.getElementById('edit-year').value = data.year;
        document.getElementById('edit-company').value = data.company.id;
        document.getElementById('editModal').classList.remove('hidden');
    });
}

// Cierra el modal de edición
function closeEditModal() {
    document.getElementById('editModal').classList.add('hidden');
}

// Envía el formulario de edición por AJAX
function submitEditForm(event) {
    event.preventDefault();
    const id = document.getElementById('edit-id').value;
    const name = document.getElementById('edit-name').value;
    const year = document.getElementById('edit-year').value;
    const company = document.getElementById('edit-company').value;

    fetch(`/reports/${id}/update/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ name, year, company })
    }).then(response => {
        if (response.ok) {
            location.reload();
        }
    });
}