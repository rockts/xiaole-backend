const MOBILE_BREAKPOINT = 768;

export function initNavigation() {
    const overlay = document.getElementById('sidebarOverlay');
    if (overlay) {
        overlay.addEventListener('click', toggleSidebar, { passive: true });
    }

    const menuToggle = document.querySelector('.menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', (event) => {
            event.preventDefault();
            toggleSidebar();
        });
    }

    const collapseBtn = document.getElementById('sidebarCollapseBtn');
    if (collapseBtn) {
        collapseBtn.addEventListener('click', (event) => {
            event.preventDefault();
            toggleSidebarCollapse();
        });
    }

    document.querySelectorAll('.nav-item[data-tab]').forEach((item) => {
        item.addEventListener('click', (event) => {
            event.preventDefault();
            const tabName = item.dataset.tab;
            if (tabName) {
                switchTab(tabName, event);
            }
        });
    });
}

export function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (!sidebar) return;

    const isMobile = window.innerWidth <= MOBILE_BREAKPOINT;
    if (isMobile) {
        sidebar.classList.toggle('mobile-open');
        if (overlay) {
            overlay.classList.toggle('active');
        }
    } else {
        sidebar.classList.toggle('collapsed');
    }
}

export function toggleSidebarCollapse() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (!sidebar) return;

    const isMobile = window.innerWidth <= MOBILE_BREAKPOINT;

    if (isMobile) {
        sidebar.classList.toggle('mobile-open');
        if (overlay) {
            overlay.classList.toggle('active');
        }
    } else {
        sidebar.classList.toggle('collapsed');
    }
}

export function switchTab(tabName, event) {
    // 移除所有标签和导航项的激活状态
    document.querySelectorAll('.tab').forEach((tab) => tab.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach((item) => item.classList.remove('active'));

    // 隐藏所有内容区域(包括聊天区域和功能页面)
    document.querySelectorAll('.tab-content').forEach((content) => {
        content.classList.remove('active');
    });

    // 隐藏首页欢迎区
    const homeHero = document.getElementById('homeHero');
    if (homeHero) {
        homeHero.style.display = 'none';
    }

    const navItem = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (navItem) {
        navItem.classList.add('active');
    }

    if (event && event.target && event.target.classList && event.target.classList.contains('tab')) {
        event.target.classList.add('active');
    } else {
        const tabButton = document.querySelector(`.tab[onclick*="${tabName}"]`);
        if (tabButton) {
            tabButton.classList.add('active');
        }
    }

    const contentEl = document.getElementById(tabName);
    if (contentEl) {
        contentEl.classList.add('active');
    }

    const titleMap = {
        chat: '对话',
        sessions: '历史对话',
        memory: '记忆',
        reminders: '提醒',
        tasks: '任务',
        documents: '文档',
        schedule: '课程表',
        tools: '工具',
        settings: '设置'
    };
    const pageTitle = document.getElementById('pageTitle');
    if (pageTitle) {
        const label = titleMap[tabName] || '小乐 AI 管家';
        pageTitle.textContent = label;
    }

    if (window.innerWidth <= MOBILE_BREAKPOINT) {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        if (sidebar) sidebar.classList.remove('mobile-open');
        if (overlay) overlay.classList.remove('active');
    }

    if (tabName === 'sessions' && typeof loadSessions === 'function') loadSessions();
    if (tabName === 'memory' && typeof loadMemoryStats === 'function') loadMemoryStats();
    if (tabName === 'analytics') {
        if (typeof loadBehaviorAnalytics === 'function') loadBehaviorAnalytics();
        if (typeof loadProactiveQA === 'function') loadProactiveQA('default_user');
    }
    if (tabName === 'tasks' && typeof loadTasks === 'function') {
        const statusFilter = document.getElementById('taskStatusFilter');
        if (statusFilter) statusFilter.value = 'pending';
        loadTasks();
    }
    if (tabName === 'reminders') {
        if (typeof loadReminders === 'function') loadReminders();
        if (typeof loadReminderHistory === 'function') loadReminderHistory();
    }
    if (tabName === 'documents' && typeof loadDocuments === 'function') loadDocuments();
    if (tabName === 'tools') {
        if (typeof loadTools === 'function') loadTools();
        if (typeof loadToolHistory === 'function') loadToolHistory();
    }
    if (tabName === 'schedule' && typeof loadSchedule === 'function') loadSchedule();
}
