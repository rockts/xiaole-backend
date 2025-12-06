/**
 * reminders_tasks.js
 * 提醒与任务管理模块：加载、创建、切换、删除、检查
 */

let showExpired = false; // 提醒显示模式状态

export function initRemindersTasks() {
    // 绑定任务区域按钮
    document.querySelectorAll('[data-action="tasks-refresh"]').forEach(btn => btn.addEventListener('click', loadTasks));
    document.querySelectorAll('[data-action="task-create"]').forEach(btn => btn.addEventListener('click', showCreateTaskDialog));
    const statusFilter = document.getElementById('taskStatusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', loadTasks);
    }

    // 绑定提醒区域按钮
    document.querySelectorAll('[data-action="reminders-refresh"]').forEach(btn => btn.addEventListener('click', loadReminders));
    document.querySelectorAll('[data-action="reminder-create"]').forEach(btn => btn.addEventListener('click', showCreateReminderDialog));
    document.querySelectorAll('[data-action="reminder-toggle-expired"]').forEach(btn => btn.addEventListener('click', toggleExpiredReminders));
    document.querySelectorAll('[data-action="reminder-check"]').forEach(btn => btn.addEventListener('click', checkReminders));

    // 事件委托：提醒卡片中的操作按钮
    document.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('[data-reminder-toggle]');
        if (toggleBtn) {
            const id = toggleBtn.getAttribute('data-reminder-toggle');
            toggleReminder(id);
            return;
        }
        const delBtn = e.target.closest('[data-reminder-delete]');
        if (delBtn) {
            const id = delBtn.getAttribute('data-reminder-delete');
            deleteReminder(id);
            return;
        }
        const taskDetailBtn = e.target.closest('[data-task-detail]');
        if (taskDetailBtn) {
            const id = taskDetailBtn.getAttribute('data-task-detail');
            showTaskDetails(id);
            return;
        }
        const taskExecuteBtn = e.target.closest('[data-task-execute]');
        if (taskExecuteBtn) {
            const id = taskExecuteBtn.getAttribute('data-task-execute');
            executeTask(id);
            return;
        }
        const taskCancelBtn = e.target.closest('[data-task-cancel]');
        if (taskCancelBtn) {
            const id = taskCancelBtn.getAttribute('data-task-cancel');
            cancelTask(id);
            return;
        }
        const taskDeleteBtn = e.target.closest('[data-task-delete]');
        if (taskDeleteBtn) {
            const id = taskDeleteBtn.getAttribute('data-task-delete');
            deleteTask(id);
            return;
        }
    });
}

// ===================== 提醒管理 =====================

export async function loadReminders() {
    const container = document.getElementById('remindersList');
    if (!container) return;
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const response = await fetch(`${window.API_BASE}/api/reminders?user_id=default_user&enabled_only=false`);
        const data = await response.json();
        const reminders = data.reminders || [];

        if (reminders.length === 0) {
            container.innerHTML = '<div style="color:#999;text-align:center;padding:20px;">还没有提醒，点击"创建提醒"来添加！</div>';
            updateReminderStats(0, 0, 0);
            return;
        }

        // 统计
        let activeCount = 0, disabledCount = 0, triggeredCount = 0;
        reminders.forEach(r => {
            if (r.trigger_count > 0 || r.last_triggered) {
                triggeredCount++;
            } else if (r.enabled) {
                activeCount++;
            } else {
                disabledCount++;
            }
        });
        updateReminderStats(activeCount, disabledCount, triggeredCount);

        // 过滤
        let displayReminders = showExpired ? reminders : reminders.filter(r => !r.trigger_count && !r.last_triggered);
        if (displayReminders.length === 0) {
            container.innerHTML = showExpired
                ? '<div style="color:#999;text-align:center;padding:20px;">没有提醒记录。</div>'
                : '<div style="color:#999;text-align:center;padding:20px;">没有待触发的提醒。<br><br>点击"👁️ 显示已过期"查看已触发的提醒。</div>';
            return;
        }

        container.innerHTML = `<div style="display:grid;gap:15px;">${displayReminders.map(renderReminderCard).join('')}</div>`;

        // 启动倒计时
        displayReminders.forEach(r => {
            if (!r.last_triggered && !r.trigger_count && r.reminder_type === 'time') {
                updateCountdown(r.reminder_id, r.trigger_condition);
            }
        });
    } catch (err) {
        container.innerHTML = `<div class='error'>加载失败: ${err.message}</div>`;
    }
}

function renderReminderCard(reminder) {
    const priorityColors = {
        1: { color: '#ef4444', emoji: '🔴', label: '最高' },
        2: { color: '#f59e0b', emoji: '🟠', label: '高' },
        3: { color: '#eab308', emoji: '🟡', label: '中' },
        4: { color: '#10b981', emoji: '🟢', label: '低' },
        5: { color: '#6b7280', emoji: '⚪', label: '最低' }
    };
    const priority = priorityColors[reminder.priority] || priorityColors[3];
    const isTriggered = reminder.trigger_count > 0 || reminder.last_triggered;
    const statusColor = isTriggered ? '#9ca3af' : (reminder.enabled ? '#10b981' : '#9ca3af');
    const statusText = isTriggered ? '已触发' : (reminder.enabled ? '启用' : '禁用');
    const cardBg = isTriggered ? '#f3f4f6' : 'white';
    const cardOpacity = isTriggered ? 'opacity:0.8;' : '';
    const typeEmoji = { time: '⏰', weather: '🌤️', behavior: '👤', habit: '🎯' };

    return `<div style='background:${cardBg};padding:15px;border-radius:10px;border-left:4px solid ${priority.color};${cardOpacity}'>
        <div style='display:flex;justify-content:space-between;align-items:start;margin-bottom:10px;'>
            <div style='flex:1;'>
                <div style='font-size:16px;font-weight:bold;color:#333;margin-bottom:5px;'>${priority.emoji} ${reminder.title || '无标题'} ${isTriggered ? '<span style="font-size:12px;color:#9ca3af;margin-left:8px;">📜 已触发</span>' : ''}</div>
                <div style='font-size:14px;color:#666;margin-bottom:8px;'>${reminder.content}</div>
                ${!isTriggered && reminder.reminder_type === 'time' ? `<div id='countdown-${reminder.reminder_id}' style='font-size:13px;color:#667eea;margin-bottom:8px;font-weight:500;'>⏳ 计算中...</div>` : ''}
                <div style='display:flex;gap:10px;flex-wrap:wrap;font-size:12px;'>
                    <span style='background:#e0e7ff;color:#4f46e5;padding:3px 8px;border-radius:4px;'>${typeEmoji[reminder.reminder_type] || '📌'} ${reminder.reminder_type}</span>
                    <span style='background:${statusColor}20;color:${statusColor};padding:3px 8px;border-radius:4px;'>● ${statusText}</span>
                    <span style='background:${priority.color}20;color:${priority.color};padding:3px 8px;border-radius:4px;'>优先级: ${priority.label}</span>
                    ${reminder.repeat ? '<span style="background:#fef3c7;color:#d97706;padding:3px 8px;border-radius:4px;">🔄 重复</span>' : ''}
                </div>
            </div>
            <div style='display:flex;gap:5px;margin-left:10px;'>
                ${!isTriggered ? `<button data-reminder-toggle='${reminder.reminder_id}' style='padding:6px 12px;background:${reminder.enabled ? '#ef4444' : '#10b981'};color:#fff;border:none;border-radius:5px;cursor:pointer;font-size:12px;'>${reminder.enabled ? '禁用' : '启用'}</button>` : ''}
                <button data-reminder-delete='${reminder.reminder_id}' style='padding:6px 12px;background:#dc2626;color:#fff;border:none;border-radius:5px;cursor:pointer;font-size:12px;'>删除</button>
            </div>
        </div>
        ${reminder.last_triggered ? `<div style='font-size:11px;color:#999;margin-top:5px;'>上次触发: ${new Date(reminder.last_triggered).toLocaleString('zh-CN')} ${reminder.trigger_count ? ` | 触发次数: ${reminder.trigger_count}` : ''}</div>` : ''}
    </div>`;
}

function updateReminderStats(active, disabled, triggered) {
    const a = document.getElementById('activeCount');
    const d = document.getElementById('disabledCount');
    const t = document.getElementById('triggeredCount');
    if (a) a.textContent = active; if (d) d.textContent = disabled; if (t) t.textContent = triggered;
}

function updateCountdown(reminderId, triggerCondition) {
    try {
        const condition = typeof triggerCondition === 'string' ? JSON.parse(triggerCondition) : triggerCondition;
        const target = new Date(condition.datetime.replace(' ', 'T'));
        function tick() {
            const el = document.getElementById(`countdown-${reminderId}`);
            if (!el) return;
            const diff = target.getTime() - Date.now();
            if (diff <= 0) { el.textContent = '⏰ 即将触发'; return; }
            const hours = Math.floor(diff / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);
            el.textContent = `⏳ 剩余 ${hours}小时 ${minutes}分 ${seconds}秒`;
            requestAnimationFrame(tick);
        }
        tick();
    } catch (e) { console.warn('倒计时解析失败', e); }
}

export function toggleExpiredReminders() {
    showExpired = !showExpired;
    const btn = document.getElementById('toggleExpiredBtn');
    if (btn) btn.textContent = showExpired ? '👁️ 隐藏已过期' : '👁️ 显示已过期';
    loadReminders();
}

export async function checkReminders() {
    try {
        const response = await fetch(`${window.API_BASE}/api/reminders/check`, { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showNotification('✅ 已检查提醒', 'success');
            loadReminders();
        } else {
            showNotification('❌ 检查失败', 'error');
        }
    } catch (e) {
        showNotification('❌ 检查失败: 网络错误', 'error');
    }
}

export function showCreateReminderDialog() {
    // 禁用创建提醒对话框
    return;
    const dialog = `
    <div class='reminder-dialog-overlay' id='reminderDialog' style='position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;justify-content:center;align-items:center;z-index:1000;'>
      <div style='background:#fff;padding:25px;border-radius:15px;max-width:500px;width:90%;'>
        <h3 style='margin:0 0 20px;color:#667eea;'>➕ 创建新提醒</h3>
        <div style='margin-bottom:15px;'>
          <label style='display:block;margin-bottom:5px;font-weight:bold;'>标题:</label>
          <input type='text' id='reminderTitle' style='width:100%;padding:10px;border:2px solid #ddd;border-radius:8px;'>
        </div>
        <div style='margin-bottom:15px;'>
          <label style='display:block;margin-bottom:5px;font-weight:bold;'>内容:</label>
          <textarea id='reminderContent' rows='3' style='width:100%;padding:10px;border:2px solid #ddd;border-radius:8px;'></textarea>
        </div>
        <div style='margin-bottom:15px;'>
          <label style='display:block;margin-bottom:5px;font-weight:bold;'>触发时间:</label>
          <input type='datetime-local' id='reminderTime' style='width:100%;padding:10px;border:2px solid #ddd;border-radius:8px;'>
        </div>
        <div style='margin-bottom:15px;'>
          <label style='display:block;margin-bottom:5px;font-weight:bold;'>优先级:</label>
          <select id='reminderPriority' style='width:100%;padding:10px;border:2px solid #ddd;border-radius:8px;'>
            <option value='1'>🔴 最高</option>
            <option value='2'>🟠 高</option>
            <option value='3' selected>🟡 中</option>
            <option value='4'>🟢 低</option>
            <option value='5'>⚪ 最低</option>
          </select>
        </div>
        <div style='display:flex;gap:10px;justify-content:flex-end;margin-top:20px;'>
          <button data-action='reminder-cancel' style='padding:10px 20px;background:#9ca3af;color:#fff;border:none;border-radius:8px;cursor:pointer;'>取消</button>
          <button data-action='reminder-create-confirm' style='padding:10px 20px;background:#10b981;color:#fff;border:none;border-radius:8px;cursor:pointer;'>创建</button>
        </div>
      </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', dialog);
    const overlay = document.getElementById('reminderDialog');
    if (overlay) {
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeReminderDialog(); });
    }
    document.querySelector('[data-action="reminder-cancel"]').addEventListener('click', closeReminderDialog);
    document.querySelector('[data-action="reminder-create-confirm"]').addEventListener('click', createReminder);
}

function closeReminderDialog() {
    const dialog = document.getElementById('reminderDialog');
    if (dialog) dialog.remove();
}

async function createReminder() {
    const title = document.getElementById('reminderTitle').value.trim();
    const content = document.getElementById('reminderContent').value.trim();
    const time = document.getElementById('reminderTime').value;
    const priority = parseInt(document.getElementById('reminderPriority').value);

    if (!content) { alert('请输入提醒内容'); return; }
    if (!time) { alert('请选择触发时间'); return; }

    try {
        const response = await fetch(`${window.API_BASE}/api/reminders`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: 'default_user',
                reminder_type: 'time',
                trigger_condition: { datetime: time.replace('T', ' ') + ':00' },
                title: title || '新提醒',
                content,
                priority,
                repeat: false
            })
        });
        const data = await response.json();
        if (data.success) {
            closeReminderDialog();
            loadReminders();
            alert('✅ 提醒创建成功！');
        } else {
            alert('❌ 创建失败: ' + (data.error || '未知错误'));
        }
    } catch (e) { alert('❌ 创建失败: ' + e.message); }
}

async function toggleReminder(reminderId) {
    try {
        const resp = await fetch(`${window.API_BASE}/api/reminders/${reminderId}/toggle`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) loadReminders(); else alert('操作失败');
    } catch (e) { alert('操作失败: ' + e.message); }
}

async function deleteReminder(reminderId) {
    if (!confirm('确定要删除这条提醒吗？')) return;
    try {
        const resp = await fetch(`${window.API_BASE}/api/reminders/${reminderId}`, { method: 'DELETE' });
        const data = await resp.json();
        if (data.success) { loadReminders(); alert('✅ 删除成功'); } else { alert('❌ 删除失败'); }
    } catch (e) { alert('❌ 删除失败: ' + e.message); }
}

// ===================== 任务管理 =====================

export async function loadTasks() {
    const container = document.getElementById('tasksList');
    if (!container) return;
    container.innerHTML = '<div class="loading">加载中...</div>';
    try {
        const statusFilter = document.getElementById('taskStatusFilter')?.value || '';
        const userId = 'default_user';
        let url = `${window.API_BASE}/api/users/${userId}/tasks?limit=50`;
        if (statusFilter) url += `&status=${statusFilter}`;
        const response = await fetch(url);
        const data = await response.json();
        if (!data.success) throw new Error(data.error || '加载任务失败');
        const tasks = data.tasks || [];
        updateTaskStats(tasks);
        if (tasks.length === 0) { container.innerHTML = '<div class="loading">暂无任务</div>'; return; }
        tasks.sort((a, b) => {
            if (a.priority !== b.priority) return b.priority - a.priority;
            if (a.status !== b.status) {
                const order = ['in_progress', 'pending', 'waiting', 'failed', 'completed', 'cancelled'];
                return order.indexOf(a.status) - order.indexOf(b.status);
            }
            return new Date(b.created_at) - new Date(a.created_at);
        });
        container.innerHTML = `<div>${tasks.map(renderTaskCard).join('')}</div>`;
    } catch (e) {
        container.innerHTML = `<div class='error'>加载失败: ${e.message}</div>`;
    }
}

function renderTaskCard(task) {
    const statusMap = { pending: '待处理', in_progress: '执行中', waiting: '等待中', completed: '已完成', failed: '失败', cancelled: '已取消' };
    const priorityMap = { 0: '普通', 1: '重要', 2: '紧急' };
    const progress = task.total_steps > 0 ? Math.round((task.current_step / task.total_steps) * 100) : 0;
    const statusClass = task.status; const statusText = statusMap[task.status] || task.status;
    const priorityText = priorityMap[task.priority] || '普通';
    const createdTime = new Date(task.created_at).toLocaleString('zh-CN');
    const updatedTime = task.updated_at ? new Date(task.updated_at).toLocaleString('zh-CN') : '-';
    return `<div class='task-card status-${statusClass}'>
      <div class='task-header'>
        <div style='flex:1;'>
          <div class='task-title'>${escapeHtml(task.title)}</div>
          ${task.description ? `<div class='task-description'>${escapeHtml(task.description)}</div>` : ''}
        </div>
        <div style='display:flex;gap:8px;align-items:flex-start;'>
          <span class='priority-badge priority-${task.priority}'>${priorityText}</span>
          <span class='task-status-badge ${statusClass}'>${statusText}</span>
        </div>
      </div>
      ${task.total_steps > 0 ? `<div class='task-progress'><div class='task-progress-bar'><div class='task-progress-fill' style='width:${progress}%'></div></div><div class='task-progress-text'>${task.current_step}/${task.total_steps}</div></div>` : ''}
      <div class='task-meta'>
        <span>📅 创建: ${createdTime}</span>
        <span>🔄 更新: ${updatedTime}</span>
        ${task.retry_count > 0 ? `<span>🔁 重试: ${task.retry_count}次</span>` : ''}
      </div>
      <div class='task-actions'>
        <button class='task-btn task-btn-primary' data-task-detail='${task.id}'>📋 详情</button>
        ${(task.status === 'pending' || task.status === 'waiting') ? `<button class='task-btn task-btn-success' data-task-execute='${task.id}'>▶️ 执行</button>` : ''}
        ${(task.status === 'in_progress' || task.status === 'waiting') ? `<button class='task-btn task-btn-secondary' data-task-cancel='${task.id}'>⏸️ 取消</button>` : ''}
        ${(task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') ? `<button class='task-btn task-btn-danger' data-task-delete='${task.id}'>🗑️ 删除</button>` : ''}
      </div>
    </div>`;
}

function updateTaskStats(tasks) {
    const stats = { pending: 0, in_progress: 0, completed: 0, failed: 0 };
    tasks.forEach(t => { if (stats.hasOwnProperty(t.status)) stats[t.status]++; });
    const m = (id) => document.getElementById(id);
    if (m('taskPendingCount')) m('taskPendingCount').textContent = stats.pending;
    if (m('taskInProgressCount')) m('taskInProgressCount').textContent = stats.in_progress;
    if (m('taskCompletedCount')) m('taskCompletedCount').textContent = stats.completed;
    if (m('taskFailedCount')) m('taskFailedCount').textContent = stats.failed;
}

export function showCreateTaskDialog() {
    return; // 禁用对话框
    const html = `
    <div class='custom-notification-overlay' style='position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:10001;'>
      <div style='background:var(--card-bg);padding:25px;border-radius:12px;box-shadow:0 8px 24px var(--shadow-heavy);max-width:90%;max-height:80vh;overflow-y:auto;'>
        <h3 style='margin:0 0 15px;'>创建新任务</h3>
        <div style='margin:15px 0;'>
          <label style='display:block;margin-bottom:5px;font-weight:500;'>任务标题:</label>
          <input type='text' id='newTaskTitle' style='width:100%;padding:10px;border:2px solid #ddd;border-radius:8px;'>
        </div>
        <div style='margin:15px 0;'>
          <label style='display:block;margin-bottom:5px;font-weight:500;'>任务描述:</label>
          <textarea id='newTaskDesc' rows='3' style='width:100%;padding:10px;border:2px solid #ddd;border-radius:8px;resize:vertical;'></textarea>
        </div>
        <div style='margin:15px 0;'>
          <label style='display:block;margin-bottom:5px;font-weight:500;'>优先级:</label>
          <select id='newTaskPriority' style='width:100%;padding:10px;border:2px solid #ddd;border-radius:8px;'>
            <option value='0'>普通</option>
            <option value='1'>重要</option>
            <option value='2'>紧急</option>
          </select>
        </div>
        <div style='display:flex;gap:10px;margin-top:20px;'>
          <button data-action='task-create-confirm' style='flex:1;padding:12px;background:#667eea;color:#fff;border:none;border-radius:8px;cursor:pointer;'>✅ 创建</button>
          <button data-action='task-create-cancel' style='flex:1;padding:12px;background:#6b7280;color:#fff;border:none;border-radius:8px;cursor:pointer;'>❌ 取消</button>
        </div>
      </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
    const overlay = document.querySelector('.custom-notification-overlay');
    if (overlay) overlay.addEventListener('click', (e) => { if (e.target === overlay) closeCustomNotification(); });
    document.querySelector('[data-action="task-create-confirm"]').addEventListener('click', createTask);
    document.querySelector('[data-action="task-create-cancel"]').addEventListener('click', closeCustomNotification);
}

function createTask() {
    const title = document.getElementById('newTaskTitle').value.trim();
    const description = document.getElementById('newTaskDesc').value.trim();
    const priority = parseInt(document.getElementById('newTaskPriority').value);
    if (!title) { showNotification('❌ 请输入任务标题', 'error'); return; }
    fetch(`${window.API_BASE}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'default_user', session_id: window.currentSessionId || '', title, description, priority })
    }).then(r => r.json()).then(data => {
        if (!data.success) throw new Error(data.error || '创建任务失败');
        showNotification('✅ 任务创建成功', 'success');
        closeCustomNotification();
        loadTasks();
    }).catch(err => { showNotification(`❌ 创建失败: ${err.message}`, 'error'); });
}

function closeCustomNotification() { const overlay = document.querySelector('.custom-notification-overlay'); if (overlay) overlay.remove(); }

// Placeholder stubs for task actions (to be modularized later if needed)
function showTaskDetails(id) { console.log('showTaskDetails', id); }
function executeTask(id) { console.log('executeTask', id); }
function cancelTask(id) { console.log('cancelTask', id); }
function deleteTask(id) { console.log('deleteTask', id); }

// Helpers
function escapeHtml(str) { return str ? str.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#39;' }[c])) : ''; }
function showNotification(message, type) { if (window.showNotification) { window.showNotification(message, type); } else { console.log(`[${type}] ${message}`); } }
