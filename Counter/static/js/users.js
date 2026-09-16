document.addEventListener('DOMContentLoaded', () => {
  const getCSRF = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  };

  const routes = {
    create       : '/users/create/',
    update       : '/users/update/',
    toggleActive : id => `/users/${id}/toggle-active/`,
    expert       : id => `/users/${id}/expert/`,
  };

  const showError = (el, msg) => {
    el.textContent = msg;
    el.classList.remove('hidden');
  };

  /* ------------------------------------------------------------------ */
  /* Modal crear                                                         */
  /* ------------------------------------------------------------------ */
  const createModal  = document.getElementById('createUserModal');
  const createForm   = document.getElementById('create-user-form');
  const createError  = document.getElementById('create-error');

  window.openCreateModal = () => {
    createError.classList.add('hidden');
    createModal.classList.remove('hidden');
  };
  window.closeCreateModal = () => createModal.classList.add('hidden');

  createForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    createError.classList.add('hidden');

    const payload = {
      username  : document.getElementById('cu-username').value.trim(),
      email     : document.getElementById('cu-email').value.trim(),
      password  : document.getElementById('cu-password').value,
      profession: document.getElementById('cu-profession').value.trim(),
      is_staff  : document.getElementById('cu-is-staff').checked,
      is_active : document.getElementById('cu-is-active').checked,
    };

    try {
      const res = await fetch(routes.create, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRF() },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(createError, data.error || 'No se pudo crear el usuario.');
        return;
      }
      window.location.reload();
    } catch (err) {
      showError(createError, 'Error de conexión.');
    }
  });

  /* ------------------------------------------------------------------ */
  /* Modal editar                                                        */
  /* ------------------------------------------------------------------ */
  const editModal = document.getElementById('editUserModal');
  const editForm  = document.getElementById('edit-user-form');
  const editError = document.getElementById('edit-error');

  window.openEditModal = (btn) => {
    editError.classList.add('hidden');
    document.getElementById('eu-user-id').value     = btn.dataset.id;
    document.getElementById('eu-username').value    = btn.dataset.username;
    document.getElementById('eu-email').value       = btn.dataset.email;
    document.getElementById('eu-profession').value  = btn.dataset.profession;
    document.getElementById('eu-is-staff').checked  = btn.dataset.isStaff === '1';
    document.getElementById('eu-is-active').checked = btn.dataset.isActive === '1';
    editModal.classList.remove('hidden');
  };
  window.closeEditModal = () => editModal.classList.add('hidden');

  document.querySelectorAll('.edit-user-btn').forEach((btn) => {
    btn.addEventListener('click', () => window.openEditModal(btn));
  });

  editForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    editError.classList.add('hidden');

    const payload = {
      user_id    : document.getElementById('eu-user-id').value,
      username   : document.getElementById('eu-username').value.trim(),
      email      : document.getElementById('eu-email').value.trim(),
      profession : document.getElementById('eu-profession').value.trim(),
      is_staff   : document.getElementById('eu-is-staff').checked,
      is_active  : document.getElementById('eu-is-active').checked,
    };

    try {
      const res = await fetch(routes.update, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRF() },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(editError, data.error || 'No se pudo actualizar el usuario.');
        return;
      }
      window.location.reload();
    } catch (err) {
      showError(editError, 'Error de conexión.');
    }
  });

  /* ------------------------------------------------------------------ */
  /* Activar / desactivar                                                */
  /* ------------------------------------------------------------------ */
  document.querySelectorAll('.toggle-user-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const action = btn.dataset.active === '1' ? 'desactivar' : 'activar';
      if (!window.confirm(`¿${action[0].toUpperCase() + action.slice(1)} a este usuario?`)) return;

      try {
        const res = await fetch(routes.toggleActive(btn.dataset.id), {
          method: 'POST',
          headers: { 'X-CSRFToken': getCSRF() },
        });
        const data = await res.json();
        if (!res.ok) {
          window.alert(data.error || 'No se pudo cambiar el estado.');
          return;
        }
        window.location.reload();
      } catch (err) {
        window.alert('Error de conexión.');
      }
    });
  });

  /* ------------------------------------------------------------------ */
  /* Modal experto                                                       */
  /* ------------------------------------------------------------------ */
  const expertModal = document.getElementById('expertUserModal');
  const expertForm  = document.getElementById('expert-user-form');
  const expertError = document.getElementById('expert-error');

  window.openExpertUserModal = (btn) => {
    expertError.classList.add('hidden');
    document.getElementById('xu-user-id').value      = btn.dataset.id;
    document.getElementById('xu-username').textContent = btn.dataset.username;
    document.getElementById('xu-profession').value   = btn.dataset.profession;
    document.getElementById('xu-profession').placeholder = btn.dataset.profession ? btn.dataset.profession : '';
    expertModal.classList.remove('hidden');
  };
  window.closeExpertUserModal = () => expertModal.classList.add('hidden');

  document.querySelectorAll('.expert-user-btn').forEach((btn) => {
    btn.addEventListener('click', () => window.openExpertUserModal(btn));
  });

  expertForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    expertError.classList.add('hidden');

    const payload = { profession: document.getElementById('xu-profession').value.trim() };

    try {
      const res = await fetch(routes.expert(document.getElementById('xu-user-id').value), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRF() },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(expertError, data.error || 'No se pudo asignar el experto.');
        return;
      }
      window.location.reload();
    } catch (err) {
      showError(expertError, 'Error de conexión.');
    }
  });

  document.getElementById('xu-remove').addEventListener('click', async () => {
    if (!window.confirm('¿Quitar a este usuario como experto?')) return;

    try {
      const res = await fetch(routes.expert(document.getElementById('xu-user-id').value), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRF() },
        body: JSON.stringify({ remove: true }),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(expertError, data.error || 'No se pudo quitar el experto.');
        return;
      }
      window.location.reload();
    } catch (err) {
      showError(expertError, 'Error de conexión.');
    }
  });
});