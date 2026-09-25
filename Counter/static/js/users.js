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
    del          : id => `/users/${id}/delete/`,
    auditLogs    : '/users/audit-logs/',
  };

  const showError = (el, msg) => {
    el.textContent = msg;
    el.classList.remove('hidden');
  };

  /* ------------------------------------------------------------------ */
  /* Modal crear usuario                                                */
  /* ------------------------------------------------------------------ */
  const createModal  = document.getElementById('createUserModal');
  const createForm   = document.getElementById('create-user-form');
  const createError  = document.getElementById('create-error');

  window.openCreateModal = () => {
    if (createError) createError.classList.add('hidden');
    if (createForm) createForm.reset();
    createModal.classList.remove('hidden');
  };
  window.closeCreateModal = () => createModal.classList.add('hidden');

  if (createForm) {
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
        showError(createError, 'Error de conexión con el servidor.');
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Modal editar usuario                                               */
  /* ------------------------------------------------------------------ */
  const editModal = document.getElementById('editUserModal');
  const editForm  = document.getElementById('edit-user-form');
  const editError = document.getElementById('edit-error');

  window.openEditModal = (btn) => {
    if (editError) editError.classList.add('hidden');
    document.getElementById('eu-user-id').value     = btn.dataset.id;
    document.getElementById('eu-username').value    = btn.dataset.username;
    document.getElementById('eu-email').value       = btn.dataset.email;
    document.getElementById('eu-profession').value  = btn.dataset.profession || '';
    document.getElementById('eu-is-staff').checked  = btn.dataset.isStaff === '1';
    document.getElementById('eu-is-active').checked = btn.dataset.isActive === '1';
    editModal.classList.remove('hidden');
  };
  window.closeEditModal = () => editModal.classList.add('hidden');

  document.querySelectorAll('.edit-user-btn').forEach((btn) => {
    btn.addEventListener('click', () => window.openEditModal(btn));
  });

  if (editForm) {
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
        showError(editError, 'Error de conexión con el servidor.');
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Activar / Desactivar (Toggle)                                      */
  /* ------------------------------------------------------------------ */
  document.querySelectorAll('.toggle-user-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const isCurrentlyActive = btn.dataset.active === '1';
      const actionText = isCurrentlyActive ? 'desactivar temporalmente' : 'activar';
      if (!window.confirm(`¿Estás seguro de que deseas ${actionText} a este usuario?`)) return;

      try {
        const res = await fetch(routes.toggleActive(btn.dataset.id), {
          method: 'POST',
          headers: { 'X-CSRFToken': getCSRF() },
        });
        const data = await res.json();
        if (!res.ok) {
          window.alert(data.error || 'No se pudo cambiar el estado del usuario.');
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
    if (expertError) expertError.classList.add('hidden');
    document.getElementById('xu-user-id').value      = btn.dataset.id;
    document.getElementById('xu-username').textContent = btn.dataset.username;
    document.getElementById('xu-profession').value   = btn.dataset.profession || '';
    document.getElementById('xu-profession').placeholder = btn.dataset.profession ? btn.dataset.profession : 'Ej. Perito Legal';
    expertModal.classList.remove('hidden');
  };
  window.closeExpertUserModal = () => expertModal.classList.add('hidden');

  document.querySelectorAll('.expert-user-btn').forEach((btn) => {
    btn.addEventListener('click', () => window.openExpertUserModal(btn));
  });

  if (expertForm) {
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
          showError(expertError, data.error || 'No se pudo asignar la especialidad.');
          return;
        }
        window.location.reload();
      } catch (err) {
        showError(expertError, 'Error de conexión.');
      }
    });
  }

  const xuRemoveBtn = document.getElementById('xu-remove');
  if (xuRemoveBtn) {
    xuRemoveBtn.addEventListener('click', async () => {
      if (!window.confirm('¿Quitar a este usuario como experto?')) return;

      try {
        const res = await fetch(routes.expert(document.getElementById('xu-user-id').value), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRF() },
          body: JSON.stringify({ remove: true }),
        });
        const data = await res.json();
        if (!res.ok) {
          showError(expertError, data.error || 'No se pudo quitar la especialidad.');
          return;
        }
        window.location.reload();
      } catch (err) {
        showError(expertError, 'Error de conexión.');
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Soft Delete (Baja Lógica Segura)                                    */
  /* ------------------------------------------------------------------ */
  document.querySelectorAll('.delete-user-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const username = btn.dataset.username;
      const isAlreadyDeleted = btn.dataset.isDeleted === '1';

      if (isAlreadyDeleted) {
        // Opción de reactivar si ya estaba dado de baja
        if (!window.confirm(`El usuario "${username}" está dado de baja lógica. ¿Deseas reactivar su cuenta para que pueda volver a iniciar sesión?`)) return;

        try {
          const res = await fetch(routes.toggleActive(btn.dataset.id), {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRF() },
          });
          const data = await res.json();
          if (!res.ok) {
            window.alert(data.error || 'No se pudo reactivar al usuario.');
            return;
          }
          window.location.reload();
        } catch (err) {
          window.alert('Error de conexión.');
        }
        return;
      }

      // Confirmación informativa de baja lógica
      const confirmMsg = `¿Dar de baja lógica al usuario "${username}"?\n\n• Su cuenta será desactivada y no podrá iniciar sesión.\n• Su historial de auditorías, documentos y reportes se conservará intacto.`;
      if (!window.confirm(confirmMsg)) return;

      try {
        const res = await fetch(routes.del(btn.dataset.id), {
          method: 'POST',
          headers: { 'X-CSRFToken': getCSRF() },
        });
        const data = await res.json();
        if (!res.ok) {
          window.alert(data.error || 'No se pudo dar de baja al usuario.');
          return;
        }
        window.location.reload();
      } catch (err) {
        window.alert('Error de conexión.');
      }
    });
  });

  /* ------------------------------------------------------------------ */
  /* Modal Historial de Auditoría y Trazabilidad                         */
  /* ------------------------------------------------------------------ */
  const auditModal = document.getElementById('auditLogsModal');
  const auditLogsList = document.getElementById('auditLogsList');
  const auditFilterAction = document.getElementById('auditFilterAction');
  let currentAuditUserId = null;

  window.openAuditModal = async (userId = null) => {
    currentAuditUserId = userId;
    auditModal.classList.remove('hidden');
    await loadAuditLogs();
  };
  window.closeAuditModal = () => auditModal.classList.add('hidden');

  async function loadAuditLogs() {
    if (!auditLogsList) return;
    auditLogsList.innerHTML = `
      <div class="py-12 text-center text-gray-500">
        <svg class="animate-spin h-6 w-6 mx-auto mb-2 text-blue-600" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
        </svg>
        <p class="text-sm">Cargando registros de auditoría...</p>
      </div>
    `;

    let url = routes.auditLogs;
    const params = new URLSearchParams();
    if (currentAuditUserId) params.append('user_id', currentAuditUserId);
    if (auditFilterAction && auditFilterAction.value) params.append('action', auditFilterAction.value);

    if ([...params].length > 0) url += `?${params.toString()}`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok || !data.success) {
        auditLogsList.innerHTML = `<p class="p-6 text-center text-sm text-red-600">Error al cargar registros.</p>`;
        return;
      }

      if (data.logs.length === 0) {
        auditLogsList.innerHTML = `
          <div class="py-12 text-center text-gray-400">
            <svg class="w-10 h-10 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <p class="text-sm font-medium">No se encontraron eventos registrados.</p>
          </div>
        `;
        return;
      }

      const getActionBadge = (action, display) => {
        let colors = 'bg-blue-50 text-blue-700 border-blue-200';
        if (action === 'CREATE') colors = 'bg-green-50 text-green-700 border-green-200';
        if (action === 'SOFT_DELETE') colors = 'bg-red-50 text-red-700 border-red-200';
        if (action === 'RESTORE') colors = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        if (action === 'ROLE_CHANGE') colors = 'bg-purple-50 text-purple-700 border-purple-200';
        if (action === 'LOGIN') colors = 'bg-sky-50 text-sky-700 border-sky-200';
        return `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${colors}">${display}</span>`;
      };

      auditLogsList.innerHTML = data.logs.map(log => `
        <div class="p-4 hover:bg-gray-50/80 transition flex items-start space-x-3.5 border-b border-gray-100 last:border-b-0">
          <div class="w-8 h-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between mb-1">
              <div class="flex items-center space-x-2">
                ${getActionBadge(log.action, log.action_display)}
                <span class="text-xs font-bold text-gray-800">${log.target}</span>
              </div>
              <span class="text-xs text-gray-400 font-mono">${log.timestamp}</span>
            </div>
            <p class="text-sm text-gray-700 leading-snug">${log.description}</p>
            <div class="mt-1 flex items-center space-x-3 text-xs text-gray-400">
              <span>Por: <strong class="text-gray-600 font-medium">${log.actor}</strong></span>
              <span>•</span>
              <span>IP: <code class="font-mono text-gray-500">${log.ip_address}</code></span>
            </div>
          </div>
        </div>
      `).join('');

    } catch (err) {
      auditLogsList.innerHTML = `<p class="p-6 text-center text-sm text-red-600">Error de conexión al cargar auditoría.</p>`;
    }
  }

  if (auditFilterAction) {
    auditFilterAction.addEventListener('change', loadAuditLogs);
  }

  // Vincular botones para abrir historial
  document.querySelectorAll('.open-audit-btn').forEach(btn => {
    btn.addEventListener('click', () => window.openAuditModal(btn.dataset.userId || null));
  });
});
