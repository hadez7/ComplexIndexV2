document.addEventListener('DOMContentLoaded', () => {
  /* Helpers ---------------------------------------------------------------- */

  const modal        = document.getElementById('expertModal');
  const modalTitle   = document.getElementById('modalTitle');
  const listForm     = document.getElementById('list-form');
  const listIdInput  = document.getElementById('list-id');
  const listNameInp  = document.getElementById('list-name');
  const listWordsInp = document.getElementById('list-words'); // <- ¡Ahora sí está aquí!

  // Endpoints
  const routes = {
    create: '/expert_lists/create/',
    update: id => `/expert_lists/${id}/update/`,
    del   : id => `/expert_lists/${id}/delete/`,
  };

  const getCSRF = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  };

  const openModal   = () => modal.classList.remove('hidden');
  window.closeModal = () => modal.classList.add('hidden');

  /* Modal para nueva lista ------------------------------------------------ */
  window.openNewListModal = (btn) => {
    listForm.dataset.expertId = btn.dataset.expertId;
    listIdInput.value   = '';
    listNameInp.value   = '';
    listWordsInp.value  = '';
    modalTitle.textContent = 'Nueva Lista de Expertos';
    openModal();
  };

  window.openExpertModal = () => {
      document
          .getElementById("expertCreateModal")
          .classList.remove("hidden");
  };

  window.closeExpertModal = () => {
      document
          .getElementById("expertCreateModal")
          .classList.add("hidden");
  };

  const expertForm = document.getElementById('expert-form');

  expertForm?.addEventListener('submit', (e) => {
      e.preventDefault();

      fetch('/expert_lists/expert/create/', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCSRF(),
          },
          body: JSON.stringify({
              user_id: document.getElementById('expert-user').value,
              profession: document.getElementById('expert-profession').value
          })
      })

      .then(async r => {
          const data = await r.json();

          if (r.ok && data.success) {
              location.reload();
          } else {
              alert(data.error || 'Error al guardar');
          }
      });
  });

  /* Borrar lista ---------------------------------------------------------- */
  document.querySelectorAll('.delete-list-btn').forEach(btn => {
    
    btn.addEventListener('click', () => {
      if (!confirm('¿Eliminar esta lista?')) return;

      fetch(routes.del(btn.dataset.id), {
        method : 'POST',
        headers: { 'X-CSRFToken': getCSRF() },
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          document.getElementById(`list-row-${btn.dataset.id}`)?.remove();
        }
      });
    });
  });


  /* --- NUEVO: abrir modal de edición ------------------------------------ */
  window.openEditListModal = (btn) => {
    listForm.dataset.expertId = btn.dataset.expertId;
    listIdInput.value  = btn.dataset.id;          // ← ID para diferenciar create/update
    listNameInp.value  = btn.dataset.name;
    listWordsInp.value = btn.dataset.words || '';  // ← Carga palabras existentes
    modalTitle.textContent = 'Editar lista';

    openModal();
  };

  /* Activar los botones “Editar” */
  document.querySelectorAll('.edit-list-btn').forEach(btn =>
    btn.addEventListener('click', () => openEditListModal(btn))
  );

  /* --- Envío del formulario -------------------------------------------- */
  listForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const listId   = listIdInput.value;
    const expertId = listForm.dataset.expertId;

    const body = { name: listNameInp.value };

    const wordsRaw = listWordsInp.value.trim();
    body.words = wordsRaw
      ? wordsRaw.split(',').map(w => w.trim()).filter(Boolean)
      : [];

    if (!listId) body.expert_id = expertId;

    fetch(listId ? routes.update(listId) : routes.create, {
      method : 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken' : getCSRF(),
      },
      body: JSON.stringify(body)
    })
    .then(async r => {
      const data = await r.json();

      if (r.ok && data.success) {
        location.reload();
      } else {
        alert(data.error || 'Error al guardar la lista');
      }
    })
    .catch(err => {
      console.error(err);
      alert('Error de conexión');
    });
  });


});
