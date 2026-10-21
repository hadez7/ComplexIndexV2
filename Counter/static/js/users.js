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
  /* Control dinámico de roles (Auditor / Experto / Admin)               */
  /* ------------------------------------------------------------------ */
  window.setRoleRadio = (mode, role) => {
    const prefix = mode === 'create' ? 'cu' : 'eu';
    const radio = document.querySelector(`input[name="${prefix}-role"][value="${role}"]`);
    if (radio) {
      radio.checked = true;
    }
    window.toggleRoleFields(mode);
  };

  window.toggleRoleFields = (mode) => {
    const isCreate = mode === 'create';
    const prefix = isCreate ? 'cu' : 'eu';
    const roleRadio = document.querySelector(`input[name="${prefix}-role"]:checked`);
    const role = roleRadio ? roleRadio.value : 'auditor';

    // Feedback visual de las 3 tarjetas de rol
    document.querySelectorAll(`input[name="${prefix}-role"]`).forEach((radio) => {
      const card = radio.closest('.role-card');
      if (!card) return;
      card.classList.toggle('is-selected', radio.checked);
    });

    const expertContainer = document.getElementById(isCreate ? 'cu-expert-fields' : 'eu-expert-fields');
    const professionSelect = document.getElementById(isCreate ? 'cu-profession' : 'eu-profession');
    const wsHint = document.getElementById('cu-workspace-hint');

    // La elección de profesiones SOLO debe aparecer cuando se seleccione Experto
    if (role === 'expert') {
      if (expertContainer) expertContainer.classList.remove('hidden');
      if (professionSelect) professionSelect.required = true;
      if (isCreate && wsHint) {
        wsHint.textContent = 'Obligatorio para que el experto pueda acceder de inmediato a los reportes de opacidad.';
        wsHint.className = 'mt-1 text-[9px] font-medium text-[var(--violet)]';
      }
    } else {
      if (expertContainer) expertContainer.classList.add('hidden');
      if (professionSelect) {
        professionSelect.required = false;
        professionSelect.value = '';
      }
      if (isCreate && wsHint) {
        wsHint.textContent = 'Vincula al usuario a este proyecto para que acceda inmediatamente sin bloqueos.';
        wsHint.className = 'mt-1 text-[9px] text-[var(--muted)]';
      }
    }
  };

  /* ------------------------------------------------------------------ */
  /* Modal crear usuario                                                */
  /* ------------------------------------------------------------------ */
  const createModal  = document.getElementById('createUserModal');
  const createForm   = document.getElementById('create-user-form');
  const createError  = document.getElementById('create-error');

  window.openCreateModal = () => {
    if (createError) createError.classList.add('hidden');
    if (createForm) {
      createForm.reset();
      const defaultRole = document.querySelector('input[name="cu-role"][value="auditor"]');
      if (defaultRole) defaultRole.checked = true;
      window.toggleRoleFields('create');
    }
    createModal.classList.remove('hidden');
  };
  window.closeCreateModal = () => createModal.classList.add('hidden');

  if (createForm) {
    createForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      createError.classList.add('hidden');

      const roleRadio = document.querySelector('input[name="cu-role"]:checked');
      const role = roleRadio ? roleRadio.value : 'auditor';
      const profession = document.getElementById('cu-profession').value.trim();
      const workspaceElem = document.getElementById('cu-workspace');
      const workspaceId = workspaceElem && workspaceElem.value ? workspaceElem.value : null;

      if (role === 'expert' && !profession) {
        showError(createError, 'Debes seleccionar una especialidad del catálogo oficial para el rol de Experto.');
        return;
      }

      const payload = {
        username    : document.getElementById('cu-username').value.trim(),
        email       : document.getElementById('cu-email').value.trim(),
        password    : document.getElementById('cu-password').value,
        role        : role,
        profession  : role === 'expert' ? profession : '',
        workspace_id: workspaceId,
        is_active   : document.getElementById('cu-is-active').checked,
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
    if (!btn) return;
    const button = (btn.closest && btn.closest('.edit-user-btn')) ? btn.closest('.edit-user-btn') : btn;
    if (editError) editError.classList.add('hidden');

    const idInput = document.getElementById('eu-user-id');
    if (idInput) idInput.value = button.dataset.id || '';

    const userInput = document.getElementById('eu-username');
    if (userInput) userInput.value = button.dataset.username || '';

    const emailInput = document.getElementById('eu-email');
    if (emailInput) emailInput.value = button.dataset.email || '';

    const pwdInput = document.getElementById('eu-password');
    if (pwdInput) pwdInput.value = '';

    const role = button.dataset.role || (button.dataset.isStaff === '1' ? 'admin' : (button.dataset.profession ? 'expert' : 'auditor'));
    const roleRadio = document.querySelector(`input[name="eu-role"][value="${role}"]`);
    if (roleRadio) roleRadio.checked = true;

    // Actualiza tarjetas y muestra/oculta el selector de profesión
    window.toggleRoleFields('edit');

    const profSelect = document.getElementById('eu-profession');
    if (role === 'expert' && profSelect) {
      profSelect.value = button.dataset.profession || '';
    }

    const wsSelect = document.getElementById('eu-workspace');
    if (wsSelect) wsSelect.value = button.dataset.workspaceId || '';

    const activeCheckbox = document.getElementById('eu-is-active');
    if (activeCheckbox) activeCheckbox.checked = button.dataset.isActive === '1';

    if (editModal) editModal.classList.remove('hidden');
  };
  window.closeEditModal = () => {
    if (editModal) editModal.classList.add('hidden');
  };

  document.querySelectorAll('.edit-user-btn').forEach((btn) => {
    btn.addEventListener('click', () => window.openEditModal(btn));
  });

  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      editError.classList.add('hidden');

      const roleRadio = document.querySelector('input[name="eu-role"]:checked');
      const role = roleRadio ? roleRadio.value : 'auditor';
      const profession = document.getElementById('eu-profession').value.trim();
      const workspaceElem = document.getElementById('eu-workspace');
      const workspaceId = workspaceElem && workspaceElem.value ? workspaceElem.value : null;

      if (role === 'expert' && !profession) {
        showError(editError, 'Debes seleccionar una especialidad del catálogo oficial para el rol de Experto.');
        return;
      }

      const payload = {
        user_id     : document.getElementById('eu-user-id').value,
        username    : document.getElementById('eu-username').value.trim(),
        email       : document.getElementById('eu-email').value.trim(),
        role        : role,
        profession  : role === 'expert' ? profession : '',
        workspace_id: workspaceId,
        is_active   : document.getElementById('eu-is-active').checked,
      };

      const newPassword = document.getElementById('eu-password') ? document.getElementById('eu-password').value : '';
      if (newPassword) {
        payload.password = newPassword;
      }

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
      const username = btn.dataset.username || 'este usuario';
      const confirmMsg = isCurrentlyActive
        ? `¿Suspender temporalmente a "${username}"?\n\nEl usuario no podrá iniciar sesión mientras permanezca suspendido.`
        : `¿Reactivar el acceso de "${username}"?`;
      if (!window.confirm(confirmMsg)) return;

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

      // Confirmación informativa de baja lógica (eliminación segura)
      const confirmMsg = `¿Eliminar al usuario "${username}"?\n\n• Se aplicará una baja lógica: la cuenta quedará inhabilitada para acceder.\n• Su historial de reportes, auditorías y documentos se conservará intacto por trazabilidad.\n• Podrás restaurar su cuenta en cualquier momento.`;
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
      <div class="py-12 text-center text-[var(--muted)]">
        <svg class="mx-auto mb-2 h-6 w-6 animate-spin text-[var(--blue)]" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
        </svg>
        <p class="text-[10px]">Cargando registros de auditoría...</p>
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
        auditLogsList.innerHTML = `<p class="p-6 text-center text-[10px] text-[var(--red)]">Error al cargar registros.</p>`;
        return;
      }

      if (data.logs.length === 0) {
        auditLogsList.innerHTML = `
          <div class="py-12 text-center text-[var(--faint)]">
            <svg class="mx-auto mb-2 h-9 w-9 text-[var(--faint)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <p class="text-[10px] font-medium">No se encontraron eventos registrados.</p>
          </div>
        `;
        return;
      }

      const getActionBadge = (action, display) => {
        let colors = 'border-[var(--line)] bg-[var(--blue-soft)] text-[var(--blue)]';
        if (action === 'CREATE') colors = 'border-[var(--line)] bg-[var(--teal-soft)] text-[var(--teal)]';
        if (action === 'SOFT_DELETE') colors = 'border-[var(--line)] bg-[var(--red-soft)] text-[var(--red)]';
        if (action === 'RESTORE') colors = 'border-[var(--line)] bg-[var(--teal-soft)] text-[var(--teal)]';
        if (action === 'ROLE_CHANGE') colors = 'border-[var(--line)] bg-[var(--violet-soft)] text-[var(--violet)]';
        if (action === 'LOGIN') colors = 'border-[var(--line)] bg-[var(--indigo-soft)] text-[var(--indigo)]';
        return `<span class="inline-flex items-center rounded-full border px-2 py-0.5 text-[8px] font-semibold ${colors}">${display}</span>`;
      };

      auditLogsList.innerHTML = data.logs.map(log => `
        <div class="flex items-start gap-3 border-b border-[var(--line)] p-4 transition last:border-b-0 hover:bg-[var(--surface-hover)]">
          <div class="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[var(--surface-hover)] text-[var(--muted)]">
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div class="min-w-0 flex-1">
            <div class="mb-1 flex items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                ${getActionBadge(log.action, log.action_display)}
                <span class="text-[10px] font-semibold text-[var(--ink)]">${log.target}</span>
              </div>
              <span class="font-mono text-[9px] text-[var(--faint)]">${log.timestamp}</span>
            </div>
            <p class="text-[10px] leading-5 text-[var(--muted)]">${log.description}</p>
            <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] text-[var(--faint)]">
              <span>Por: <strong class="font-medium text-[var(--muted)]">${log.actor}</strong></span>
              <span>•</span>
              <span>IP: <code class="font-mono text-[var(--muted)]">${log.ip_address}</code></span>
            </div>
          </div>
        </div>
      `).join('');

    } catch (err) {
      auditLogsList.innerHTML = `<p class="p-6 text-center text-[10px] text-[var(--red)]">Error de conexión al cargar auditoría.</p>`;
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
