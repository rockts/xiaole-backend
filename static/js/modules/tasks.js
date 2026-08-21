/** 旧静态客户端的任务管理模块。 */

export function initTasks() {
    document.querySelectorAll('[data-action="tasks-refresh"]').forEach(
        btn => btn.addEventListener('click', loadTasks)
    );
    document.querySelectorAll('[data-action="task-create"]').forEach(
        btn => btn.addEventListener('click', showCreateTaskDialog)
    );
    const statusFilter = document.getElementById('taskStatusFilter');
    if (statusFilter) statusFilter.addEventListener('change', loadTasks);

    document.addEventListener('click', (event) => {
        const actions = [
            ['data-task-detail', showTaskDetails],
            ['data-task-execute', executeTask],
            ['data-task-cancel', cancelTask],
            ['data-task-delete', deleteTask],
        ];
        for (const [attribute, handler] of actions) {
            const button = event.target.closest(`[${attribute}]`);
            if (button) {
                handler(button.getAttribute(attribute));
                return;
            }
        }
    });
}

export async function loadTasks() {
    const container = document.getElementById('tasksList');
    if (!container) return;
    container.innerHTML = '<div class="loading">加载中...</div>';
    try {
        const status = document.getElementById('taskStatusFilter')?.value || '';
        let url = `${window.API_BASE}/api/users/default_user/tasks?limit=50`;
        if (status) url += `&status=${status}`;
        const response = await fetch(url);
        const data = await response.json();
        if (!data.success) throw new Error(data.error || '加载任务失败');
        const tasks = data.tasks || [];
        updateTaskStats(tasks);
        if (tasks.length === 0) {
            container.innerHTML = '<div class="loading">暂无任务</div>';
            return;
        }
        tasks.sort((a, b) => {
            if (a.priority !== b.priority) return b.priority - a.priority;
            return new Date(b.created_at) - new Date(a.created_at);
        });
        container.innerHTML = `<div>${tasks.map(renderTaskCard).join('')}</div>`;
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

function renderTaskCard(task) {
    const statusMap = {
        pending: '待处理', in_progress: '执行中', waiting: '等待中',
        completed: '已完成', failed: '失败', cancelled: '已取消'
    };
    const priorityMap = { 0: '普通', 1: '重要', 2: '紧急' };
    const progress = task.total_steps > 0
        ? Math.round((task.current_step / task.total_steps) * 100) : 0;
    const statusText = statusMap[task.status] || task.status;
    return `<div class="task-card status-${task.status}">
      <div class="task-header"><div style="flex:1;">
        <div class="task-title">${escapeHtml(task.title)}</div>
        ${task.description ? `<div class="task-description">${escapeHtml(task.description)}</div>` : ''}
      </div><div style="display:flex;gap:8px;align-items:flex-start;">
        <span class="priority-badge priority-${task.priority}">${priorityMap[task.priority] || '普通'}</span>
        <span class="task-status-badge ${task.status}">${statusText}</span>
      </div></div>
      ${task.total_steps > 0 ? `<div class="task-progress"><div class="task-progress-bar"><div class="task-progress-fill" style="width:${progress}%"></div></div><div class="task-progress-text">${task.current_step}/${task.total_steps}</div></div>` : ''}
      <div class="task-actions">
        <button class="task-btn task-btn-primary" data-task-detail="${task.id}">📋 详情</button>
        ${(task.status === 'pending' || task.status === 'waiting') ? `<button class="task-btn task-btn-success" data-task-execute="${task.id}">▶️ 执行</button>` : ''}
        ${(task.status === 'in_progress' || task.status === 'waiting') ? `<button class="task-btn task-btn-secondary" data-task-cancel="${task.id}">⏸️ 取消</button>` : ''}
        ${(task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') ? `<button class="task-btn task-btn-danger" data-task-delete="${task.id}">🗑️ 删除</button>` : ''}
      </div></div>`;
}

function updateTaskStats(tasks) {
    const stats = { pending: 0, in_progress: 0, completed: 0, failed: 0 };
    tasks.forEach(task => { if (task.status in stats) stats[task.status] += 1; });
    for (const [id, status] of [
        ['taskPendingCount', 'pending'], ['taskInProgressCount', 'in_progress'],
        ['taskCompletedCount', 'completed'], ['taskFailedCount', 'failed']
    ]) {
        const element = document.getElementById(id);
        if (element) element.textContent = stats[status];
    }
}

export function showCreateTaskDialog() {
    // 旧静态客户端不再创建任务；对话入口负责新任务流程。
}

function showTaskDetails(id) { console.log('showTaskDetails', id); }
function executeTask(id) { console.log('executeTask', id); }
function cancelTask(id) { console.log('cancelTask', id); }
function deleteTask(id) { console.log('deleteTask', id); }
function escapeHtml(value) {
    return value ? value.replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[char])) : '';
}
