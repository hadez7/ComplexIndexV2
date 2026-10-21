document.addEventListener('DOMContentLoaded', () => {
  /* ==========================================================================
     Variables y Referencias DOM
     ========================================================================== */
  const modal            = document.getElementById('expertModal');
  const modalTitle       = document.getElementById('modalTitle');
  const listForm         = document.getElementById('list-form');
  const listIdInput      = document.getElementById('list-id');
  const listNameInp      = document.getElementById('list-name');
  const listWordsInp     = document.getElementById('list-words');
  const wordsCountBadge  = document.getElementById('wordsCountBadge');

  // Búsqueda en tiempo real
  const searchInput      = document.getElementById('expertSearchInput');
  const searchClearBtn   = document.getElementById('expertSearchClear');
  const searchMatchCount = document.getElementById('searchMatchCount');
  const noSearchResults = document.getElementById('noSearchResults');
  const expertCards      = document.querySelectorAll('.expert-card');

  // Endpoints API
  const routes = {
    create: '/expert_lists/create/',
    update: id => `/expert_lists/${id}/update/`,
    del   : id => `/expert_lists/${id}/delete/`,
  };

  const getCSRF = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  };

  /* ==========================================================================
     Contador Dinámico de Términos en el Textarea
     ========================================================================== */
  const updateWordsCount = () => {
    if (!listWordsInp || !wordsCountBadge) return;
    const raw = listWordsInp.value.trim();
    if (!raw) {
      wordsCountBadge.textContent = '0 términos';
      return;
    }
    const count = raw.split(/[,;\n]+/).map(w => w.trim()).filter(Boolean).length;
    wordsCountBadge.textContent = `${count} término${count !== 1 ? 's' : ''}`;
  };

  listWordsInp?.addEventListener('input', updateWordsCount);

  /* ==========================================================================
     Control del Modal de Lista (Crear / Editar)
     ========================================================================== */
  const openModal   = () => modal?.classList.remove('hidden');
  window.closeModal = () => modal?.classList.add('hidden');

  window.openNewListModal = (btn) => {
    if (!listForm) return;
    listForm.dataset.expertId = btn.dataset.expertId;
    if (listIdInput) listIdInput.value = '';
    if (listNameInp) listNameInp.value = '';
    if (listWordsInp) listWordsInp.value = '';
    updateWordsCount();
    if (modalTitle) modalTitle.textContent = 'Nueva Lista de Expertos';
    openModal();
    setTimeout(() => listNameInp?.focus(), 50);
  };

  window.openEditListModal = (btn) => {
    if (!listForm) return;
    listForm.dataset.expertId = btn.dataset.expertId;
    if (listIdInput) listIdInput.value = btn.dataset.id;
    if (listNameInp) listNameInp.value = btn.dataset.name;
    if (listWordsInp) listWordsInp.value = btn.dataset.words || '';
    updateWordsCount();
    if (modalTitle) modalTitle.textContent = 'Editar Lista';
    openModal();
    setTimeout(() => listNameInp?.focus(), 50);
  };

  document.querySelectorAll('.edit-list-btn').forEach(btn =>
    btn.addEventListener('click', () => openEditListModal(btn))
  );

  /* Guardar / Editar Lista vía AJAX */
  listForm?.addEventListener('submit', (e) => {
    e.preventDefault();

    const listId   = listIdInput?.value;
    const expertId = listForm.dataset.expertId;
    const rawWords = listWordsInp?.value || '';

    const body = {
      name: listNameInp.value.trim(),
      words: rawWords
        ? rawWords.split(/[,;\n]+/).map(w => w.trim()).filter(Boolean)
        : []
    };

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
      alert('Error de conexión al procesar la lista.');
    });
  });

  /* ==========================================================================
     Control del Modal de Asignación de Experto
     ========================================================================== */
  window.openExpertModal = () => {
    document.getElementById("expertCreateModal")?.classList.remove("hidden");
  };

  window.closeExpertModal = () => {
    document.getElementById("expertCreateModal")?.classList.add("hidden");
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
        user_id: document.getElementById('expert-user')?.value,
        profession: document.getElementById('expert-profession')?.value
      })
    })
    .then(async r => {
      const data = await r.json();
      if (r.ok && data.success) {
        location.reload();
      } else {
        alert(data.error || 'Error al guardar el perfil de experto.');
      }
    })
    .catch(err => {
      console.error(err);
      alert('Error de conexión al registrar experto.');
    });
  });

  /* ==========================================================================
     Eliminación de Listas con Modal de Confirmación
     ========================================================================== */
  const deleteModal = document.getElementById('deleteListModal');
  const confirmDeleteBtn = document.getElementById('confirmDeleteListBtn');
  let listIdToDelete = null;

  window.openDeleteListModal = (id, name) => {
    listIdToDelete = id;
    const nameSpan = document.getElementById('deleteListNameSpan');
    if (nameSpan && name) {
      nameSpan.textContent = '"' + name + '"';
    } else if (nameSpan) {
      nameSpan.textContent = '';
    }
    deleteModal?.classList.remove('hidden');
  };

  window.closeDeleteListModal = () => {
    listIdToDelete = null;
    deleteModal?.classList.add('hidden');
  };

  document.querySelectorAll('.delete-list-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      openDeleteListModal(btn.dataset.id, btn.dataset.name);
    });
  });

  confirmDeleteBtn?.addEventListener('click', () => {
    if (!listIdToDelete) return;
    const currentId = listIdToDelete;

    fetch(routes.del(currentId), {
      method : 'POST',
      headers: { 'X-CSRFToken': getCSRF() },
    })
    .then(r => r.json())
    .then(data => {
      closeDeleteListModal();
      if (data.success) {
        const row = document.getElementById(`list-row-${currentId}`);
        if (row) {
          row.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
          row.style.opacity = '0';
          row.style.transform = 'scale(0.98)';
          setTimeout(() => row.remove(), 200);
        }
      } else {
        alert(data.error || 'No se pudo eliminar la lista.');
      }
    })
    .catch(err => {
      closeDeleteListModal();
      console.error(err);
      alert('Error de conexión al eliminar la lista.');
    });
  });

  /* ==========================================================================
     Despliegue Inline de Términos (+X más)
     ========================================================================== */
  document.querySelectorAll('.toggle-terms-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const parent = btn.closest('.terms-wrapper');
      const hiddenSpan = parent?.querySelector('.hidden-terms-span');
      if (!hiddenSpan) return;

      const isHidden = hiddenSpan.classList.contains('hidden');
      if (isHidden) {
        hiddenSpan.classList.remove('hidden');
        btn.dataset.origText = btn.textContent;
        btn.textContent = 'ver menos';
      } else {
        hiddenSpan.classList.add('hidden');
        btn.textContent = btn.dataset.origText || '+ más';
      }
    });
  });

  /* ==========================================================================
     Copiar Términos al Portapapeles (Glosario Rápido)
     ========================================================================== */
  document.querySelectorAll('.copy-list-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const words = btn.dataset.words || '';
      if (!words) return;

      navigator.clipboard.writeText(words).then(() => {
        const origHtml = btn.innerHTML;
        btn.innerHTML = `
          <svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path>
          </svg>
        `;
        setTimeout(() => {
          btn.innerHTML = origHtml;
        }, 1600);
      }).catch(err => {
        console.error('Error al copiar:', err);
      });
    });
  });

  /* ==========================================================================
     Búsqueda y Filtro en Tiempo Real
     ========================================================================== */
  if (searchInput) {
    const handleSearch = () => {
      const query = searchInput.value.trim().toLowerCase();

      if (query.length > 0) {
        searchClearBtn?.classList.remove('hidden');
      } else {
        searchClearBtn?.classList.add('hidden');
      }

      let totalVisibleExperts = 0;
      let totalVisibleLists = 0;

      expertCards.forEach(card => {
        const expName = (card.dataset.expertName || '').toLowerCase();
        const expUser = (card.dataset.expertUser || '').toLowerCase();
        const expProf = (card.dataset.expertProfession || '').toLowerCase();
        const expertMatches = expName.includes(query) || expUser.includes(query) || expProf.includes(query);

        const listRows = card.querySelectorAll('.list-row');
        let visibleListsInCard = 0;

        listRows.forEach(row => {
          const listName  = (row.dataset.listName || '').toLowerCase();
          const listWords = (row.dataset.listWords || '').toLowerCase();
          const listMatches = listName.includes(query) || listWords.includes(query);

          if (!query || expertMatches || listMatches) {
            row.classList.remove('hidden');
            visibleListsInCard++;
            totalVisibleLists++;
          } else {
            row.classList.add('hidden');
          }
        });

        // La tarjeta de experto se muestra si el experto coincide o si alguna de sus listas coincide
        if (!query || expertMatches || visibleListsInCard > 0) {
          card.classList.remove('hidden');
          totalVisibleExperts++;
        } else {
          card.classList.add('hidden');
        }
      });

      // Estado de resultados
      if (searchMatchCount) {
        if (!query) {
          searchMatchCount.textContent = '';
        } else {
          searchMatchCount.textContent = `${totalVisibleExperts} experto${totalVisibleExperts !== 1 ? 's' : ''} (${totalVisibleLists} lista${totalVisibleLists !== 1 ? 's' : ''})`;
        }
      }

      // Empty State cuando nada coincide
      if (noSearchResults) {
        if (totalVisibleExperts === 0 && query.length > 0) {
          noSearchResults.classList.remove('hidden');
        } else {
          noSearchResults.classList.add('hidden');
        }
      }
    };

    searchInput.addEventListener('input', handleSearch);

    searchClearBtn?.addEventListener('click', () => {
      searchInput.value = '';
      handleSearch();
      searchInput.focus();
    });
  }

});
