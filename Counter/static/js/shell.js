// Alternar Modo Oscuro (Persistente en localStorage)
    function toggleTheme() {
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('eli_theme', isDark ? 'dark' : 'light');
        updateThemeUI(isDark);
    }

    function updateThemeUI(isDark) {
        const sIcon = document.getElementById('themeSidebarIcon');
        const tIcon = document.getElementById('themeTopIcon');
        const mIcon = document.getElementById('themeMobileIcon');
        const sLabel = document.getElementById('themeStatusLabel');
        const sunSvg = '<svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>';
        const moonSvg = '<svg class="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>';
        const iconHtml = isDark ? sunSvg : moonSvg;
        if (sIcon) sIcon.innerHTML = iconHtml;
        if (tIcon) tIcon.innerHTML = iconHtml;
        if (mIcon) mIcon.innerHTML = iconHtml;
        if (sLabel) sLabel.textContent = isDark ? 'ON' : 'OFF';
    }

    // Alternar Visibilidad Completa de la Barra Lateral (Unificado para Escritorio y Móvil/Split View)
    function toggleSidebarVisibility() {
        if (window.innerWidth < 1024) {
            // En pantallas pequeñas / vista dividida (< 1024px): alternar como drawer overlay
            const isMobileOpen = document.documentElement.classList.toggle('sidebar-mobile-open');
            const backdrop = document.getElementById('sidebarBackdrop');
            if (backdrop) {
                backdrop.classList.toggle('hidden', !isMobileOpen);
            }
            document.body.style.overflow = isMobileOpen ? 'hidden' : '';
        } else {
            // En escritorio: alternar visibilidad persistente
            const isHidden = document.documentElement.classList.toggle('sidebar-hidden');
            localStorage.setItem('eli_sidebar_hidden', isHidden ? 'true' : 'false');
        }
    }

    // Alternar Contracción de Barra Lateral (Persistente en localStorage)
    function toggleSidebarCollapse() {
        const isCollapsed = document.documentElement.classList.toggle('sidebar-collapsed');
        localStorage.setItem('eli_sidebar_collapsed', isCollapsed ? 'true' : 'false');
        updateCollapseUI(isCollapsed);
    }

    function updateCollapseUI(isCollapsed) {
        const chevron = document.getElementById('collapseChevronIcon');
        const collapseBtn = document.getElementById('sidebarCollapseBtn');
        if (chevron) {
            chevron.style.transform = isCollapsed ? 'rotate(180deg)' : '';
        }
        if (collapseBtn) {
            const expandLabel = collapseBtn.dataset.expandLabel || 'Expandir Barra';
            const collapseLabel = collapseBtn.dataset.collapseLabel || 'Colapsar Barra';
            collapseBtn.setAttribute('data-tooltip', isCollapsed ? expandLabel : collapseLabel);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Auto-descartar toasts globales sin JS inline en las plantillas.
        document.querySelectorAll('.eli-toast').forEach(function (toast) {
            setTimeout(function () {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-4px)';
                setTimeout(function () { toast.remove(); }, 300);
            }, 6000);
        });

        // Reactivar transiciones suaves para interacciones del usuario una vez que el DOM está pintado
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                document.documentElement.classList.remove('preload-transitions');
            });
        });

        // Inicializar iconos de tema
        const isDark = document.documentElement.classList.contains('dark');
        updateThemeUI(isDark);

        // Inicializar estado de icono colapso
        const isCollapsed = document.documentElement.classList.contains('sidebar-collapsed');
        updateCollapseUI(isCollapsed);

        // Helper unificado para menús desplegables (Workspace, Idioma Topbar, Usuario Sidebar)
        function initDropdown(btnId, dropdownId) {
            const btn = document.getElementById(btnId);
            const dropdown = document.getElementById(dropdownId);
            if (!btn || !dropdown) return;

            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                const isOpen = !dropdown.classList.contains('hidden');
                // Cerrar cualquier otro dropdown abierto
                document.querySelectorAll('.animate-dropdown').forEach(function (d) {
                    if (d !== dropdown) d.classList.add('hidden');
                });
                document.querySelectorAll('[aria-haspopup="true"]').forEach(function (b) {
                    if (b !== btn) b.setAttribute('aria-expanded', 'false');
                });
                dropdown.classList.toggle('hidden', isOpen);
                btn.setAttribute('aria-expanded', !isOpen);
            });

            document.addEventListener('click', function (e) {
                if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
                    dropdown.classList.add('hidden');
                    btn.setAttribute('aria-expanded', 'false');
                }
            });
        }

        initDropdown('sidebarWorkspaceBtn', 'sidebarWorkspaceDropdown');
        initDropdown('topbarLanguageBtn', 'topbarLanguageDropdown');
        initDropdown('sidebarLanguageBtn', 'sidebarLanguageDropdown');
        initDropdown('sidebarUserBtn', 'sidebarUserDropdown');

        // Limpieza de estados móviles al cambiar a tamaño de escritorio
        window.addEventListener('resize', function () {
            if (window.innerWidth >= 1024) {
                document.documentElement.classList.remove('sidebar-mobile-open');
                const backdrop = document.getElementById('sidebarBackdrop');
                if (backdrop) backdrop.classList.add('hidden');
                document.body.style.overflow = '';
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                if (document.documentElement.classList.contains('sidebar-mobile-open')) {
                    toggleSidebarVisibility();
                }
                document.querySelectorAll('.animate-dropdown').forEach(function (d) {
                    d.classList.add('hidden');
                });
                document.querySelectorAll('[aria-haspopup="true"]').forEach(function (b) {
                    b.setAttribute('aria-expanded', 'false');
                });
            }
        });

        // Highlighting Activo Inteligente de Rutas en la Barra Lateral (Máximo 1 elemento activo)
        const currentPath = window.location.pathname.replace(/\/+$/, '') || '/';
        const navLinks = Array.from(document.querySelectorAll('.sidebar-nav-item'));

        let bestMatch = null;
        let bestScore = -1;

        navLinks.forEach(function (link) {
            link.classList.remove('active');
            const rawPath = link.getAttribute('data-path');
            if (!rawPath) return;

            const linkPath = rawPath.replace(/\/+$/, '') || '/';

            if (linkPath === currentPath) {
                // Coincidencia exacta (puntuación máxima)
                const score = 1000 + linkPath.length;
                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = link;
                }
            } else if (linkPath !== '/' && currentPath.startsWith(linkPath + '/')) {
                // Coincidencia jerárquica de sub-ruta
                const score = linkPath.length;
                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = link;
                }
            }
        });

        if (bestMatch) {
            bestMatch.classList.add('active');
        }

        // Sincronizador de placeholders en selectores nativos
        function syncSelectPlaceholders() {
            document.querySelectorAll('select').forEach(function (sel) {
                function updateState() {
                    if (!sel.value || sel.value === '') {
                        sel.classList.add('placeholder-active', 'text-gray-400');
                        sel.classList.remove('text-gray-800', 'text-gray-900', 'text-gray-700');
                    } else {
                        sel.classList.remove('placeholder-active', 'text-gray-400');
                        sel.classList.add('text-gray-800');
                    }
                }
                updateState();
                sel.addEventListener('change', updateState);
            });
        }
        window.syncSelectPlaceholders = syncSelectPlaceholders;
        syncSelectPlaceholders();
    });
