// schedule.js - 课程表管理模块
// 职责：加载、从记忆解析、渲染、更新课程、保存；事件委托

let scheduleData = {
    periods: ['第1节', '第2节', '第3节', '第4节', '第5节', '第6节', '第7节'],
    weekdays: ['周一', '周二', '周三', '周四', '周五'],
    courses: {}
};
let scheduleInitialized = false;

function initSchedule() {
    if (scheduleInitialized) return;
    scheduleInitialized = true;

    const scheduleTab = document.getElementById('schedule');
    if (scheduleTab) {
        scheduleTab.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            switch (btn.getAttribute('data-action')) {
                case 'schedule-refresh':
                    loadSchedule();
                    break;
                case 'schedule-save':
                    saveSchedule();
                    break;
                default:
                    break;
            }
        });
    }

    // 课程输入委托（变化更新内存）
    const tbody = document.getElementById('scheduleBody');
    if (tbody) {
        tbody.addEventListener('change', (e) => {
            const input = e.target.closest('input[data-period][data-day]');
            if (!input) return;
            const periodIndex = input.getAttribute('data-period');
            const day = input.getAttribute('data-day');
            updateCourse(periodIndex, day, input.value);
        });
    }
}

async function loadSchedule() {
    const tbody = document.getElementById('scheduleBody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px;">加载中...</td></tr>';
    try {
        const response = await fetch(`${API_BASE}/api/schedule?user_id=default_user`);
        const data = await response.json();
        if (data.success && data.schedule) {
            scheduleData = data.schedule;
        } else {
            await parseScheduleFromMemory();
        }
        renderSchedule();
        showNotification('✅ 课程表加载成功', 'success');
    } catch (error) {
        console.error('❌ 加载课程表失败:', error);
        await parseScheduleFromMemory();
        renderSchedule();
    }
}

async function parseScheduleFromMemory() {
    try {
        const response = await fetch(`${API_BASE}/memory/search?keywords=课程表`);
        const data = await response.json();
        if (data.memories && data.memories.length > 0) {
            const scheduleMemory = data.memories[0];
            const content = scheduleMemory.content;
            const lines = content.split('\n');
            scheduleData.courses = {};
            lines.forEach(line => {
                const match = line.match(/^(周[一二三四五])[:：](.*)/);
                if (match) {
                    const day = match[1];
                    const courses = match[2].split('-');
                    courses.forEach((course, index) => {
                        if (course && course.trim()) {
                            const key = `${index}_${day}`;
                            scheduleData.courses[key] = course.trim();
                        }
                    });
                }
            });
        }
    } catch (error) {
        console.error('从记忆解析课程表失败:', error);
    }
}

function renderSchedule() {
    const tbody = document.getElementById('scheduleBody');
    if (!tbody) return;
    let html = '';
    scheduleData.periods.forEach((period, periodIndex) => {
        html += '<tr>';
        html += `<td style="font-weight: bold; background: var(--background);">${period}</td>`;
        scheduleData.weekdays.forEach((day) => {
            const key = `${periodIndex}_${day}`;
            const course = scheduleData.courses[key] || '';
            html += `<td><input type="text" value="${course}" data-period="${periodIndex}" data-day="${day}" style="width: 100%; padding: 8px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--background); color: var(--text-color);" placeholder=""></td>`;
        });
        html += '</tr>';
    });
    tbody.innerHTML = html;
}

function updateCourse(periodIndex, day, value) {
    const key = `${periodIndex}_${day}`;
    if (value && value.trim()) scheduleData.courses[key] = value.trim();
    else delete scheduleData.courses[key];
}

async function saveSchedule() {
    try {
        const response = await fetch(`${API_BASE}/api/schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: 'default_user', schedule: scheduleData })
        });
        const data = await response.json();
        if (data.success) showNotification('✅ 课程表保存成功', 'success');
        else showNotification('❌ 保存失败: ' + (data.error || '未知错误'), 'error');
    } catch (error) {
        console.error('保存课程表失败:', error);
        showNotification('❌ 保存失败: 网络错误', 'error');
    }
}

export {
    initSchedule,
    loadSchedule,
    saveSchedule,
    renderSchedule
};
