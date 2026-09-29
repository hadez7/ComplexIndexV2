/**
 * Custom Select SaaS Component
 * Transforma selectores HTML nativos en selectores estilizados con búsqueda,
 * animaciones suaves, checkmarks y soporte completo para eventos nativos de Django.
 */
(function () {
  'use strict';

  function normalizeText(text) {
    return (text || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  function initCustomSelect(select) {
    if (select.dataset.customSelectInitialized === 'true') {
      return;
    }
    select.dataset.customSelectInitialized = 'true';

    // Ocultar accesiblemente el select nativo pero manteniéndolo en el DOM para forms Django
    select.classList.add('sr-only');
    select.setAttribute('tabindex', '-1');
    select.setAttribute('aria-hidden', 'true');

    // Contenedor principal
    const wrapper = document.createElement('div');
    wrapper.className = 'custom-select-wrapper relative w-full text-left';

    // Botón Gatillo (Trigger)
    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className =
      'custom-select-trigger w-full flex items-center justify-between border border-gray-300 rounded-lg shadow-sm px-3.5 py-2.5 text-sm bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all cursor-pointer text-left';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');

    const label = document.createElement('span');
    label.className = 'custom-select-label truncate block flex-1';

    const chevron = document.createElement('span');
    chevron.className =
      'custom-select-chevron ml-2 text-gray-400 transition-transform duration-200 transform flex-shrink-0 flex items-center pointer-events-none';
    chevron.innerHTML = `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
      </svg>
    `;

    trigger.appendChild(label);
    trigger.appendChild(chevron);
    wrapper.appendChild(trigger);

    // Panel Desplegable (Dropdown Popover)
    const dropdown = document.createElement('div');
    dropdown.className =
      'custom-select-dropdown hidden absolute left-0 right-0 z-50 bg-white rounded-xl shadow-2xl border border-gray-100 overflow-hidden ring-1 ring-black ring-opacity-5 animate-dropdown';
    dropdown.style.minWidth = '100%';

    // Barra de búsqueda integrada
    const searchContainer = document.createElement('div');
    searchContainer.className = 'p-2 border-b border-gray-100 bg-gray-50/70';
    searchContainer.innerHTML = `
      <div class="relative">
        <span class="absolute inset-y-0 left-2.5 flex items-center text-gray-400 pointer-events-none">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
        </span>
        <input type="text"
               class="custom-select-search w-full pl-8 pr-3 py-1.5 text-xs text-gray-700 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-400 font-normal transition"
               placeholder="Buscar..."
               autocomplete="off"
               spellcheck="false" />
      </div>
    `;
    const searchInput = searchContainer.querySelector('.custom-select-search');
    dropdown.appendChild(searchContainer);

    // Contenedor de opciones
    const optionsList = document.createElement('div');
    optionsList.className = 'custom-select-options max-h-56 overflow-y-auto py-1 divide-y divide-gray-50';
    optionsList.setAttribute('role', 'listbox');
    dropdown.appendChild(optionsList);

    // Mensaje de sin resultados
    const emptyState = document.createElement('div');
    emptyState.className = 'custom-select-empty hidden px-4 py-4 text-xs text-gray-400 text-center';
    emptyState.textContent = 'No se encontraron resultados';
    dropdown.appendChild(emptyState);

    wrapper.appendChild(dropdown);

    // Insertar wrapper en el DOM justo antes del select nativo y mover select dentro
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(select);

    let highlightedIndex = -1;

    function syncDisabled() {
      trigger.disabled = select.disabled;
      if (select.disabled) {
        trigger.classList.add('opacity-60', 'cursor-not-allowed', 'bg-gray-50');
      } else {
        trigger.classList.remove('opacity-60', 'cursor-not-allowed', 'bg-gray-50');
      }
    }

    // Interceptar setter select.value para que cambios vía JS directo actualicen el trigger
    try {
      const descriptor = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
      if (descriptor && descriptor.set) {
        Object.defineProperty(select, 'value', {
          get: function () {
            return descriptor.get.call(this);
          },
          set: function (newVal) {
            descriptor.set.call(this, newVal);
            updateTriggerDisplay();
          },
          configurable: true
        });
      }
    } catch (e) {
      // Ignorar si el motor restringe redefinición
    }

    // Renderizar opciones desde el select nativo
    function buildOptions() {
      syncDisabled();
      optionsList.innerHTML = '';
      const options = Array.from(select.options);

      // Si hay pocas opciones (menos de 4), ocultamos la barra de búsqueda
      if (options.length < 4) {
        searchContainer.classList.add('hidden');
      } else {
        searchContainer.classList.remove('hidden');
      }

      options.forEach(function (opt, idx) {
        const item = document.createElement('div');
        item.className =
          'custom-select-item px-3.5 py-2.5 text-sm cursor-pointer flex items-center justify-between transition-colors duration-150 select-none hover:bg-blue-50 hover:text-blue-700 text-gray-700';
        item.setAttribute('role', 'option');
        item.dataset.value = opt.value;
        item.dataset.label = (opt.text || "").trim();
        item.dataset.index = idx;

        const isPlaceholder = !opt.value || opt.value === '';
        const isSelected = opt.selected || select.value === opt.value;

        const textSpan = document.createElement('span');
        textSpan.className = 'truncate';
        textSpan.textContent = (opt.text || "").trim();

        if (isPlaceholder) {
          textSpan.classList.add('text-gray-400', 'font-normal');
        }

        const checkIcon = document.createElement('span');
        checkIcon.className = 'custom-select-check ml-2 flex-shrink-0 ' + (isSelected ? 'text-blue-600' : 'hidden');
        checkIcon.innerHTML = `
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path>
          </svg>
        `;

        if (isSelected) {
          item.classList.add('bg-blue-50/70', 'text-blue-700', 'font-medium');
        }

        item.appendChild(textSpan);
        item.appendChild(checkIcon);

        item.addEventListener('click', function (e) {
          e.stopPropagation();
          selectValue(opt.value);
          closeDropdown();
          trigger.focus();
        });

        optionsList.appendChild(item);
      });

      updateTriggerDisplay();
    }

    function updateTriggerDisplay() {
      syncDisabled();
      const selectedOption = select.options[select.selectedIndex];
      const isPlaceholder = !selectedOption || !selectedOption.value || selectedOption.value === '';

      label.textContent = selectedOption ? selectedOption.text : '';

      if (isPlaceholder) {
        label.classList.add('text-gray-400', 'font-normal');
        label.classList.remove('text-gray-800', 'font-medium');
      } else {
        label.classList.remove('text-gray-400', 'font-normal');
        label.classList.add('text-gray-800', 'font-medium');
      }

      // Sincronizar checkmarks en items
      optionsList.querySelectorAll('.custom-select-item').forEach(function (it) {
        const val = it.dataset.value;
        const matches = (select.value === val);
        const check = it.querySelector('.custom-select-check');

        if (matches) {
          it.classList.add('bg-blue-50/70', 'text-blue-700', 'font-medium');
          if (check) check.classList.remove('hidden');
        } else {
          it.classList.remove('bg-blue-50/70', 'text-blue-700', 'font-medium');
          if (check) check.classList.add('hidden');
        }
      });
    }

    function selectValue(val) {
      if (select.value !== val) {
        select.value = val;
        select.dispatchEvent(new Event('change', { bubbles: true }));
      }
      updateTriggerDisplay();
    }

    function adjustPosition() {
      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const estimatedHeight = 270;

      if (spaceBelow < estimatedHeight && rect.top > estimatedHeight) {
        dropdown.classList.add('bottom-full', 'mb-1.5');
        dropdown.classList.remove('mt-1.5');
      } else {
        dropdown.classList.remove('bottom-full', 'mb-1.5');
        dropdown.classList.add('mt-1.5');
      }
    }

    function openDropdown() {
      if (select.disabled) return;

      // Cerrar otros dropdowns abiertos en la página
      document.querySelectorAll('.custom-select-dropdown:not(.hidden)').forEach(function (d) {
        if (d !== dropdown) {
          d.classList.add('hidden');
          const p = d.closest('.custom-select-wrapper');
          if (p) {
            p.style.zIndex = '';
            const t = p.querySelector('.custom-select-trigger');
            if (t) {
              t.setAttribute('aria-expanded', 'false');
              t.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
            }
            const c = p.querySelector('.custom-select-chevron');
            if (c) c.classList.remove('rotate-180', 'text-blue-600');
          }
        }
      });

      updateTriggerDisplay();
      adjustPosition();

      // Elevar z-index del wrapper activo
      wrapper.style.zIndex = '60';
      dropdown.classList.remove('hidden');
      trigger.setAttribute('aria-expanded', 'true');
      trigger.classList.add('ring-2', 'ring-blue-500', 'border-blue-500');
      chevron.classList.add('rotate-180', 'text-blue-600');

      highlightedIndex = -1;

      // Limpiar y enfocar búsqueda
      if (searchInput && !searchContainer.classList.contains('hidden')) {
        searchInput.value = '';
        filterItems('');
        setTimeout(function () {
          searchInput.focus();
        }, 30);
      } else {
        setTimeout(function () {
          trigger.focus();
        }, 30);
      }

      // Auto-scroll al elemento activo
      const activeItem = optionsList.querySelector('.custom-select-item.bg-blue-50\\/70');
      if (activeItem) {
        activeItem.scrollIntoView({ block: 'nearest' });
      }
    }

    function closeDropdown() {
      dropdown.classList.add('hidden');
      wrapper.style.zIndex = '';
      trigger.setAttribute('aria-expanded', 'false');
      trigger.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
      chevron.classList.remove('rotate-180', 'text-blue-600');
      clearHighlight();
    }

    function filterItems(query) {
      const q = normalizeText(query);
      let matchCount = 0;

      optionsList.querySelectorAll('.custom-select-item').forEach(function (item) {
        const text = normalizeText(item.dataset.label || '');
        if (!q || text.includes(q)) {
          item.classList.remove('hidden');
          matchCount++;
        } else {
          item.classList.add('hidden');
        }
      });

      if (matchCount === 0) {
        emptyState.classList.remove('hidden');
      } else {
        emptyState.classList.add('hidden');
      }
      clearHighlight();
    }

    function getVisibleItems() {
      return Array.from(optionsList.querySelectorAll('.custom-select-item:not(.hidden)'));
    }

    function clearHighlight() {
      optionsList.querySelectorAll('.custom-select-item').forEach(function (it) {
        it.classList.remove('bg-gray-100');
      });
      highlightedIndex = -1;
    }

    function highlightItem(index) {
      const visible = getVisibleItems();
      if (visible.length === 0) return;

      if (index < 0) index = 0;
      if (index >= visible.length) index = visible.length - 1;

      clearHighlight();
      highlightedIndex = index;
      const target = visible[highlightedIndex];
      if (target) {
        target.classList.add('bg-gray-100');
        target.scrollIntoView({ block: 'nearest' });
      }
    }

    // Eventos del Gatillo
    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (dropdown.classList.contains('hidden')) {
        openDropdown();
      } else {
        closeDropdown();
      }
    });

    trigger.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (dropdown.classList.contains('hidden')) {
          openDropdown();
        }
      }
    });

    if (searchInput) {
      searchInput.addEventListener('input', function () {
        filterItems(this.value);
      });
      searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
          closeDropdown();
          trigger.focus();
        } else if (e.key === 'ArrowDown') {
          e.preventDefault();
          highlightItem(highlightedIndex + 1);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          highlightItem(highlightedIndex - 1);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          const visible = getVisibleItems();
          if (highlightedIndex >= 0 && visible[highlightedIndex]) {
            selectValue(visible[highlightedIndex].dataset.value);
            closeDropdown();
            trigger.focus();
          } else if (visible.length > 0) {
            selectValue(visible[0].dataset.value);
            closeDropdown();
            trigger.focus();
          }
        }
      });
    }

    // Redireccionar focus de label nativo al trigger
    select.addEventListener('focus', function () {
      trigger.focus();
    });

    // Escuchar cambios externos en el select nativo
    select.addEventListener('change', function () {
      updateTriggerDisplay();
    });

    // Observer para reconstruir opciones si cambian dinámicamente en el select nativo
    const observer = new MutationObserver(function () {
      buildOptions();
    });
    observer.observe(select, { childList: true, subtree: true, attributes: true, attributeFilter: ['disabled', 'data-selected'] });

    // Inicializar primera construcción
    buildOptions();
  }

  // Cerrar al hacer clic fuera
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.custom-select-wrapper')) {
      document.querySelectorAll('.custom-select-dropdown:not(.hidden)').forEach(function (dropdown) {
        dropdown.classList.add('hidden');
        const wrapper = dropdown.closest('.custom-select-wrapper');
        if (wrapper) {
          wrapper.style.zIndex = '';
          const trigger = wrapper.querySelector('.custom-select-trigger');
          if (trigger) {
            trigger.setAttribute('aria-expanded', 'false');
            trigger.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
          }
          const chevron = wrapper.querySelector('.custom-select-chevron');
          if (chevron) chevron.classList.remove('rotate-180', 'text-blue-600');
        }
      });
    }
  });

  // Cerrar con Escape global
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.custom-select-dropdown:not(.hidden)').forEach(function (dropdown) {
        dropdown.classList.add('hidden');
        const wrapper = dropdown.closest('.custom-select-wrapper');
        if (wrapper) {
          wrapper.style.zIndex = '';
          const trigger = wrapper.querySelector('.custom-select-trigger');
          if (trigger) {
            trigger.setAttribute('aria-expanded', 'false');
            trigger.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
            trigger.focus();
          }
          const chevron = wrapper.querySelector('.custom-select-chevron');
          if (chevron) chevron.classList.remove('rotate-180', 'text-blue-600');
        }
      });
    }
  });

  // Inicializador global expuesto
  window.initCustomSelects = function (selector) {
    const sel = selector || 'select[data-custom-select="true"]';
    document.querySelectorAll(sel).forEach(initCustomSelect);
  };

  // Auto-iniciar al cargar el DOM
  document.addEventListener('DOMContentLoaded', function () {
    window.initCustomSelects();
  });
})();
