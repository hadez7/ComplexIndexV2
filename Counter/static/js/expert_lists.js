document.addEventListener('DOMContentLoaded', () => {
  /* ==========================================================================
     Variables y Referencias DOM
     ========================================================================== */
  const modal                 = document.getElementById('expertModal');
  const modalTitle            = document.getElementById('modalTitle');
  const listForm              = document.getElementById('list-form');
  const listIdInput           = document.getElementById('list-id');
  const listNameInp           = document.getElementById('list-name');
  const modalExpertSelect     = document.getElementById('modal-expert-select');
  const expertSelectContainer = document.getElementById('expertSelectContainer');

  // Modo píldoras vs texto masivo
  const toggleInputModeBtn    = document.getElementById('toggleInputModeBtn');
  const pillsModeContainer    = document.getElementById('pillsModeContainer');
  const rawTextModeContainer  = document.getElementById('rawTextModeContainer');
  const listWordsInp          = document.getElementById('list-words');
  const wordsCountBadge       = document.getElementById('wordsCountBadge');

  // Gestor limpio de términos
  const termQuickInput        = document.getElementById('termQuickInput');
  const addTermBtn            = document.getElementById('addTermBtn');
  const modalTermFilterInput  = document.getElementById('modalTermFilterInput');
  const termsChipsContainer   = document.getElementById('termsChipsContainer');
  const termsEmptyNotice      = document.getElementById('termsEmptyNotice');
  const clearAllTermsBtn      = document.getElementById('clearAllTermsBtn');

  // Búsqueda y Filtros de tarjetas
  const searchInput           = document.getElementById('expertSearchInput');
  const searchClearBtn        = document.getElementById('expertSearchClear');
  const searchMatchCount      = document.getElementById('searchMatchCount');
  const noSearchResults      = document.getElementById('noSearchResults');
  const vocabCards            = document.querySelectorAll('.vocab-card');
  const expertFilterBtns      = document.querySelectorAll('.expert-filter-btn');

  // Estado en memoria de los términos (lista limpia de strings)
  let termsList = [];
  let activeExpertFilter = 'all';

  // Endpoints API
  const routes = {
    create : '/expert_lists/create/',
    json   : id => `/expert_lists/${id}/json/`,
    update : id => `/expert_lists/${id}/update/`,
    del    : id => `/expert_lists/${id}/delete/`,
  };

  const getCSRF = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  };

  /* ==========================================================================
     Parser y Renderizador Limpio de Píldoras
     ========================================================================== */

  const parseRawToTerms = (raw) => {
    if (!raw) return [];
    if (Array.isArray(raw)) {
      return raw.map(item => {
        if (typeof item === 'object' && item !== null) {
          return String(item.term || '').trim();
        }
        return String(item).trim();
      }).filter(Boolean);
    }

    return String(raw)
      .split(/[,;\n]+/)
      .map(t => t.trim())
      .filter(Boolean);
  };

  const syncTermsToTextarea = () => {
    if (!listWordsInp) return;
    listWordsInp.value = termsList.join(', ');
  };

  const renderModalPills = () => {
    if (!termsChipsContainer) return;
    termsChipsContainer.innerHTML = '';

    const filterQuery = (modalTermFilterInput?.value || '').trim().toLowerCase();
    const visibleTerms = termsList.filter(t => !filterQuery || t.toLowerCase().includes(filterQuery));

    if (termsEmptyNotice) {
      termsEmptyNotice.classList.toggle('hidden', visibleTerms.length > 0);
    }

    visibleTerms.forEach((term) => {
      const chip = document.createElement('span');
      chip.className = 'term-pill';

      chip.innerHTML = `
        <span class="font-mono">${escapeHtml(term)}</span>
        <button type="button"
                class="pill-del-btn"
                title="Eliminar término">
          <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      `;

      const delBtn = chip.querySelector('.pill-del-btn');
      delBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const idx = termsList.indexOf(term);
        if (idx !== -1) {
          termsList.splice(idx, 1);
        }
        renderModalPills();
      });

      termsChipsContainer.appendChild(chip);
    });

    const total = termsList.length;
    if (wordsCountBadge) {
      wordsCountBadge.textContent = `${total} término${total !== 1 ? 's' : ''}`;
    }

    if (clearAllTermsBtn) {
      clearAllTermsBtn.classList.toggle('hidden', total === 0);
    }

    syncTermsToTextarea();
  };

  const handleAddTerm = () => {
    if (!termQuickInput) return;
    const rawVal = termQuickInput.value.trim();
    if (!rawVal) return;

    const tokens = rawVal.split(/[,;\n]+/).map(t => t.trim()).filter(Boolean);

    tokens.forEach(tok => {
      // Evitar duplicados insensibles a mayúsculas
      const exists = termsList.some(t => t.toLowerCase() === tok.toLowerCase());
      if (!exists) {
        termsList.push(tok);
      }
    });

    termQuickInput.value = '';
    renderModalPills();
    termQuickInput.focus();
  };

  addTermBtn?.addEventListener('click', handleAddTerm);
  termQuickInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTerm();
    }
  });

  modalTermFilterInput?.addEventListener('input', renderModalPills);

  clearAllTermsBtn?.addEventListener('click', () => {
    if (termsList.length === 0) return;
    termsList = [];
    renderModalPills();
  });

  /* ==========================================================================
     Alternar entre Modo Píldoras y Modo Texto Masivo
     ========================================================================== */
  toggleInputModeBtn?.addEventListener('click', () => {
    const isRawActive = !rawTextModeContainer.classList.contains('hidden');

    if (isRawActive) {
      termsList = parseRawToTerms(listWordsInp.value);
      renderModalPills();
      rawTextModeContainer.classList.add('hidden');
      pillsModeContainer.classList.remove('hidden');
      toggleInputModeBtn.textContent = 'Modo texto masivo';
    } else {
      syncTermsToTextarea();
      pillsModeContainer.classList.add('hidden');
      rawTextModeContainer.classList.remove('hidden');
      toggleInputModeBtn.textContent = 'Modo interactivo (píldoras)';
      listWordsInp?.focus();
    }
  });

  listWordsInp?.addEventListener('input', () => {
    const raw = listWordsInp.value.trim();
    const count = raw ? raw.split(/[,;\n]+/).map(w => w.trim()).filter(Boolean).length : 0;
    if (wordsCountBadge) {
      wordsCountBadge.textContent = `${count} término${count !== 1 ? 's' : ''}`;
    }
  });

  /* ==========================================================================
     Control del Botón '>' de Opciones en cada Tarjeta
     ========================================================================== */
  document.querySelectorAll('.vocab-arrow-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();

      const menu = btn.nextElementSibling;
      const isOpen = !menu?.classList.contains('hidden');

      document.querySelectorAll('.vocab-options-menu').forEach(m => m.classList.add('hidden'));
      document.querySelectorAll('.vocab-arrow-btn').forEach(b => b.classList.remove('is-active'));

      if (!isOpen && menu) {
        menu.classList.remove('hidden');
        btn.classList.add('is-active');
      }
    });
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.vocab-options-menu') && !e.target.closest('.vocab-arrow-btn')) {
      document.querySelectorAll('.vocab-options-menu').forEach(m => m.classList.add('hidden'));
      document.querySelectorAll('.vocab-arrow-btn').forEach(b => b.classList.remove('is-active'));
    }
  });

  /* ==========================================================================
     Control del Modal de Vocabulario (Crear / Editar)
     ========================================================================== */
  const openModal   = () => modal?.classList.remove('hidden');
  window.closeModal = () => modal?.classList.add('hidden');

  window.openNewListModal = (btn) => {
    if (!listForm) return;

    const expertId = btn?.dataset?.expertId || (modalExpertSelect?.value || '');
    listForm.dataset.expertId = expertId;

    if (listIdInput) listIdInput.value = '';
    if (listNameInp) listNameInp.value = '';
    if (modalExpertSelect && expertId) modalExpertSelect.value = expertId;
    if (expertSelectContainer) expertSelectContainer.classList.remove('hidden');
    if (modalTermFilterInput) modalTermFilterInput.value = '';

    termsList = [];
    renderModalPills();

    pillsModeContainer?.classList.remove('hidden');
    rawTextModeContainer?.classList.add('hidden');
    if (toggleInputModeBtn) toggleInputModeBtn.textContent = 'Modo texto masivo';

    if (modalTitle) modalTitle.textContent = 'Nuevo vocabulario controlado';
    openModal();
    setTimeout(() => listNameInp?.focus(), 60);
  };

  window.openEditListModal = (btn) => {
    if (!listForm) return;

    const listId   = btn.dataset.id;
    const expertId = btn.dataset.expertId;
    const name     = btn.dataset.name;
    const rawWords = btn.dataset.words || '';

    listForm.dataset.expertId = expertId;
    if (listIdInput) listIdInput.value = listId;
    if (listNameInp) listNameInp.value = name;
    if (modalExpertSelect && expertId) modalExpertSelect.value = expertId;
    if (modalTermFilterInput) modalTermFilterInput.value = '';

    fetch(routes.json(listId))
      .then(r => r.json())
      .then(data => {
        termsList = parseRawToTerms(data.words || rawWords);
        renderModalPills();
      })
      .catch(() => {
        termsList = parseRawToTerms(rawWords);
        renderModalPills();
      });

    pillsModeContainer?.classList.remove('hidden');
    rawTextModeContainer?.classList.add('hidden');
    if (toggleInputModeBtn) toggleInputModeBtn.textContent = 'Modo texto masivo';

    if (modalTitle) modalTitle.textContent = 'Editar vocabulario';
    openModal();
    setTimeout(() => listNameInp?.focus(), 60);
  };

  document.querySelectorAll('.edit-list-btn').forEach(btn =>
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      document.querySelectorAll('.vocab-options-menu').forEach(m => m.classList.add('hidden'));
      document.querySelectorAll('.vocab-arrow-btn').forEach(b => b.classList.remove('is-active'));
      openEditListModal(btn);
    })
  );

  /* Guardar / Editar Lista vía AJAX */
  listForm?.addEventListener('submit', (e) => {
    e.preventDefault();

    const listId   = listIdInput?.value;
    const expertId = modalExpertSelect?.value || listForm.dataset.expertId;

    if (!rawTextModeContainer?.classList.contains('hidden')) {
      termsList = parseRawToTerms(listWordsInp.value);
    }

    const body = {
      name: listNameInp.value.trim(),
      words: termsList,
    };

    if (!listId) {
      body.expert_id = expertId;
    }

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
        alert(data.error || 'Error al guardar el vocabulario');
      }
    })
    .catch(err => {
      console.error(err);
      alert('Error de conexión al procesar el vocabulario.');
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
     Eliminación de Vocabularios con Modal de Confirmación
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
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      document.querySelectorAll('.vocab-options-menu').forEach(m => m.classList.add('hidden'));
      document.querySelectorAll('.vocab-arrow-btn').forEach(b => b.classList.remove('is-active'));
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
        const card = document.getElementById(`list-row-${currentId}`);
        if (card) {
          card.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
          card.style.opacity = '0';
          card.style.transform = 'scale(0.95)';
          setTimeout(() => {
            card.remove();
            applySearchAndFilter();
          }, 250);
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
     Copiar Términos al Portapapeles (Glosario Rápido)
     ========================================================================== */
  document.querySelectorAll('.copy-list-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const words = btn.dataset.words || '';
      if (!words) return;

      navigator.clipboard.writeText(words).then(() => {
        const origHtml = btn.innerHTML;
        btn.innerHTML = `
          <svg class="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path>
          </svg>
          <span class="text-green-500 font-semibold">Copiado</span>
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
     Filtro por Especialista y Búsqueda en Tiempo Real
     ========================================================================== */
  const applySearchAndFilter = () => {
    const query = (searchInput?.value || '').trim().toLowerCase();

    if (query.length > 0) {
      searchClearBtn?.classList.remove('hidden');
    } else {
      searchClearBtn?.classList.add('hidden');
    }

    let visibleCount = 0;

    vocabCards.forEach(card => {
      const expertId   = card.dataset.expertId || '';
      const listName   = (card.dataset.listName || '').toLowerCase();
      const listWords  = (card.dataset.listWords || '').toLowerCase();
      const expertName = (card.dataset.expertName || '').toLowerCase();
      const expertUser = (card.dataset.expertUser || '').toLowerCase();
      const profession = (card.dataset.expertProfession || '').toLowerCase();

      const expertMatches = (activeExpertFilter === 'all' || expertId === activeExpertFilter);

      const textMatches = !query ||
        listName.includes(query) ||
        listWords.includes(query) ||
        expertName.includes(query) ||
        expertUser.includes(query) ||
        profession.includes(query);

      if (expertMatches && textMatches) {
        card.classList.remove('hidden');
        visibleCount++;
      } else {
        card.classList.add('hidden');
      }
    });

    if (searchMatchCount) {
      if (query || activeExpertFilter !== 'all') {
        searchMatchCount.textContent = `${visibleCount} visible${visibleCount !== 1 ? 's' : ''}`;
      } else {
        searchMatchCount.textContent = '';
      }
    }

    if (noSearchResults) {
      if (visibleCount === 0 && (query.length > 0 || activeExpertFilter !== 'all')) {
        noSearchResults.classList.remove('hidden');
      } else {
        noSearchResults.classList.add('hidden');
      }
    }
  };

  if (searchInput) {
    searchInput.addEventListener('input', applySearchAndFilter);
    searchClearBtn?.addEventListener('click', () => {
      searchInput.value = '';
      applySearchAndFilter();
      searchInput.focus();
    });
  }

  expertFilterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      expertFilterBtns.forEach(b => {
        b.classList.remove('active', 'border-[var(--blue)]', 'bg-[var(--blue-soft)]', 'text-[var(--blue)]');
        b.classList.add('border-[var(--line)]', 'bg-[var(--surface-hover)]', 'text-[var(--muted)]');
      });

      btn.classList.add('active', 'border-[var(--blue)]', 'bg-[var(--blue-soft)]', 'text-[var(--blue)]');
      btn.classList.remove('border-[var(--line)]', 'bg-[var(--surface-hover)]', 'text-[var(--muted)]');

      activeExpertFilter = btn.dataset.filterExpert || 'all';
      applySearchAndFilter();
    });
  });

  function escapeHtml(string) {
    const div = document.createElement('div');
    div.textContent = string;
    return div.innerHTML;
  }
});
