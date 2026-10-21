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

        // Dropdown del Workspace en la barra lateral
        const wsBtn = document.getElementById('sidebarWorkspaceBtn');
        const wsDropdown = document.getElementById('sidebarWorkspaceDropdown');

        // Dropdown del Selector de Idioma (Icono de Mundo)
        const langBtn = document.getElementById('sidebarLanguageBtn');
        const langDropdown = document.getElementById('sidebarLanguageDropdown');

        // Dropdown del Usuario en la barra lateral
        const userBtn = document.getElementById('sidebarUserBtn');
        const userDropdown = document.getElementById('sidebarUserDropdown');

        if (wsBtn && wsDropdown) {
            wsBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                const isOpen = !wsDropdown.classList.contains('hidden');
                wsDropdown.classList.toggle('hidden', isOpen);
                wsBtn.setAttribute('aria-expanded', !isOpen);
                // Si el selector de idioma o usuario está abierto, cerrarlos
                if (langDropdown && !langDropdown.classList.contains('hidden')) {
                    langDropdown.classList.add('hidden');
                    if (langBtn) langBtn.setAttribute('aria-expanded', 'false');
                }
                if (userDropdown && !userDropdown.classList.contains('hidden')) {
                    userDropdown.classList.add('hidden');
                    if (userBtn) userBtn.setAttribute('aria-expanded', 'false');
                }
            });

            document.addEventListener('click', function (e) {
                if (!wsDropdown.contains(e.target) && !wsBtn.contains(e.target)) {
                    wsDropdown.classList.add('hidden');
                    wsBtn.setAttribute('aria-expanded', 'false');
                }
            });
        }

        if (langBtn && langDropdown) {
            langBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                const isOpen = !langDropdown.classList.contains('hidden');
                langDropdown.classList.toggle('hidden', isOpen);
                langBtn.setAttribute('aria-expanded', !isOpen);
                // Si el selector de workspace o usuario está abierto, cerrarlos
                if (wsDropdown && !wsDropdown.classList.contains('hidden')) {
                    wsDropdown.classList.add('hidden');
                    if (wsBtn) wsBtn.setAttribute('aria-expanded', 'false');
                }
                if (userDropdown && !userDropdown.classList.contains('hidden')) {
                    userDropdown.classList.add('hidden');
                    if (userBtn) userBtn.setAttribute('aria-expanded', 'false');
                }
            });

            document.addEventListener('click', function (e) {
                if (!langDropdown.contains(e.target) && !langBtn.contains(e.target)) {
                    langDropdown.classList.add('hidden');
                    langBtn.setAttribute('aria-expanded', 'false');
                }
            });
        }

        if (userBtn && userDropdown) {
            userBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                const isOpen = !userDropdown.classList.contains('hidden');
                userDropdown.classList.toggle('hidden', isOpen);
                userBtn.setAttribute('aria-expanded', !isOpen);
                // Si el selector de workspace o idioma está abierto, cerrarlos
                if (wsDropdown && !wsDropdown.classList.contains('hidden')) {
                    wsDropdown.classList.add('hidden');
                    if (wsBtn) wsBtn.setAttribute('aria-expanded', 'false');
                }
                if (langDropdown && !langDropdown.classList.contains('hidden')) {
                    langDropdown.classList.add('hidden');
                    if (langBtn) langBtn.setAttribute('aria-expanded', 'false');
                }
            });

            document.addEventListener('click', function (e) {
                if (!userDropdown.contains(e.target) && !userBtn.contains(e.target)) {
                    userDropdown.classList.add('hidden');
                    userBtn.setAttribute('aria-expanded', 'false');
                }
            });
        }

        // Control del Drawer Móvil
        const drawerOpenBtn = document.getElementById('mobileDrawerOpenBtn');
        const drawerCloseBtn = document.getElementById('mobileDrawerCloseBtn');
        const drawerOverlay = document.getElementById('mobileDrawerOverlay');
        const drawerPanel = document.getElementById('mobileDrawerPanel');

        function openDrawer() {
            if (!drawerOverlay || !drawerPanel) return;
            drawerOverlay.classList.remove('hidden');
            setTimeout(() => {
                drawerPanel.classList.remove('-translate-x-full');
            }, 10);
            document.body.style.overflow = 'hidden';
        }

        function closeDrawer() {
            if (!drawerOverlay || !drawerPanel) return;
            drawerPanel.classList.add('-translate-x-full');
            setTimeout(() => {
                drawerOverlay.classList.add('hidden');
            }, 200);
            document.body.style.overflow = '';
        }

        if (drawerOpenBtn) drawerOpenBtn.addEventListener('click', openDrawer);
        if (drawerCloseBtn) drawerCloseBtn.addEventListener('click', closeDrawer);
        if (drawerOverlay) {
            drawerOverlay.addEventListener('click', function (e) {
                if (e.target === drawerOverlay) closeDrawer();
            });
        }

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeDrawer();
                if (wsDropdown && !wsDropdown.classList.contains('hidden')) {
                    wsDropdown.classList.add('hidden');
                    if (wsBtn) wsBtn.setAttribute('aria-expanded', 'false');
                }
                if (langDropdown && !langDropdown.classList.contains('hidden')) {
                    langDropdown.classList.add('hidden');
                    if (langBtn) langBtn.setAttribute('aria-expanded', 'false');
                }
                if (userDropdown && !userDropdown.classList.contains('hidden')) {
                    userDropdown.classList.add('hidden');
                    if (userBtn) userBtn.setAttribute('aria-expanded', 'false');
                }
            }
        });

        // Highlighting Activo Inteligente de Rutas en la Barra Lateral
        const currentPath = window.location.pathname;
        document.querySelectorAll('.sidebar-nav-item').forEach(function (link) {
            const linkPath = link.getAttribute('data-path');
            if (linkPath) {
                if (linkPath === '/' && currentPath === '/') {
                    link.classList.add('active');
                } else if (linkPath !== '/' && currentPath.startsWith(linkPath)) {
                    link.classList.add('active');
                }
            }
        });

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
