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
    ['ruc', 'name', 'province'].forEach(field => {
        const errorEl = document.getElementById('error-' + field);
        if (errorEl) errorEl.innerText = '';
    });
}

// ---------------------------------------- CREACIÓN ----------------------------------------
// Abre el modal de creación
function openCreateModal() {
    document.getElementById('createModal').classList.remove('hidden');
}

// Cierra el modal de creación y limpia el formulario
function closeCreateModal() {
    document.getElementById('createModal').classList.add('hidden');
    document.getElementById('createForm').reset();
    clearErrors();
}

// Envía el formulario de creación por AJAX
document.getElementById('createForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    clearErrors();

    const form = e.target;
    const data = new FormData(form);

    const response = await fetch(createCompanyUrl, {
        method: "POST",
        headers: { 'X-CSRFToken': csrftoken },
        body: data,
    });

    const result = await response.json();

    if (response.ok) {
        location.reload();
        addCompanyRow(result);
        hideNoCompaniesMessage();
        closeCreateModal();
    } else {
        // Muestra errores de validación
        for (const field in result.errors) {
            const errorEl = document.getElementById(`error-${field}`);
            if (errorEl) errorEl.innerText = result.errors[field].join(', ');
        }
    }
});

// Agrega una nueva fila a la tabla de empresas
function addCompanyRow(company) {
    const newRow = `
        <tr id="empresa-${company.id}" class="border-t">
            <td class="p-2">${company.ruc}</td>
            <td class="p-2">${company.name}</td>
            <td class="p-2">${company.province}</td>
            <td class="p-2 space-x-2">
                <button class="btn-details" data-id="${company.id}">Detalles</button>
                <button class="btn-edit" data-id="${company.id}">Editar</button>
                <button class="btn-delete" data-id="${company.id}">Borrar</button>
            </td>
        </tr>`;
    document.getElementById('companyTableBody').insertAdjacentHTML('beforeend', newRow);
}

// Oculta el mensaje de "no hay empresas" si existe
function hideNoCompaniesMessage() {
    const msg = document.getElementById('noCompaniesMessage');
    if (msg) msg.style.display = 'none';
}

// ---------------------------------------- DETALLES ----------------------------------------
// Muestra el modal de detalles de una empresa
function showDetails(id) {
    fetch(`/companies/${id}/json/`)
    .then(response => response.json())
    .then(data => {
        document.getElementById('detail-ruc').innerText = data.ruc;
        document.getElementById('detail-name').innerText = data.name;
        document.getElementById('detail-province').innerText = data.province;
        document.getElementById('detailsModal').classList.remove('hidden');
    });
}

// Cierra el modal de detalles
function closeDetailsModal() {
    document.getElementById('detailsModal').classList.add('hidden');
}

// ---------------------------------------- EDICIÓN ----------------------------------------
// Abre el modal de edición y llena los campos con los datos actuales
function openEditModal(id) {
    fetch(`/companies/${id}/json/`)
    .then(response => response.json())
    .then(data => {
        document.getElementById('edit-id').value = id;
        document.getElementById('edit-ruc').value = data.ruc;
        document.getElementById('edit-name').value = data.name;
        document.getElementById('edit-province').value = data.province_id;
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
    const ruc = document.getElementById('edit-ruc').value;
    const name = document.getElementById('edit-name').value;
    const province = document.getElementById('edit-province').value;

    fetch(`/companies/${id}/update/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ ruc, name, province })
    }).then(response => {
        if (response.ok) {
            // Actualiza la fila de la empresa (puedes mejorar esto para no recargar)
            location.reload();
        }
    });
}

// ---------------------------------------- ELIMINACIÓN ----------------------------------------
let companyToDelete = null;

// Abre el modal de confirmación de borrado
function openDeleteModal(id) {
    companyToDelete = id;
    document.getElementById('deleteModal').classList.remove('hidden');
}

// Cierra el modal de borrado
function closeDeleteModal() {
    companyToDelete = null;
    document.getElementById('deleteModal').classList.add('hidden');
}

// Realiza la petición AJAX para borrar la empresa
function deleteCompany() {
    fetch(`/companies/${companyToDelete}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
        }
    })
    .then(response => {
        if (response.ok) {
            document.getElementById(`empresa-${companyToDelete}`).remove();
            closeDeleteModal();
            // Si la tabla queda vacía, muestra el mensaje de "no hay empresas"
            if (!document.querySelector('#companyTableBody tr')) {
                showNoCompaniesMessage();
            }
            location.reload();
        }
    });
}

// Muestra el mensaje de "no hay empresas" si la tabla está vacía
function showNoCompaniesMessage() {
    const msg = document.getElementById('noCompaniesMessage');
    if (msg) msg.style.display = '';
}

// ---------------------------------------- EVENT DELEGATION ----------------------------------------
// Delegación de eventos para los botones de la tabla
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('btn-details')) {
        showDetails(e.target.dataset.id);
    }
    if (e.target.classList.contains('btn-edit')) {
        openEditModal(e.target.dataset.id);
    }
    if (e.target.classList.contains('btn-delete')) {
        openDeleteModal(e.target.dataset.id);
    }
});
