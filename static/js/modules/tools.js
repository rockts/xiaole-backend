// tools.js - 工具与执行历史模块
// 职责：加载工具列表、加载执行历史；事件委托；界面渲染

let toolsInitialized = false;

function initTools() {
    if (toolsInitialized) return;
    toolsInitialized = true;

    const toolsTab = document.getElementById('tools');
    if (toolsTab) {
        toolsTab.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const action = btn.getAttribute('data-action');
            switch (action) {
                case 'tools-refresh':
                    loadTools();
                    break;
                case 'tools-history-refresh':
                    loadToolHistory();
                    break;
                default:
                    break;
            }
        });
    }

    // 历史过滤 select 变化时自动刷新
    const limitSelect = document.getElementById('historyLimit');
    if (limitSelect) {
        limitSelect.addEventListener('change', () => loadToolHistory());
    }
}

async function loadTools() {
    const container = document.getElementById('toolsList');
    if (!container) return;
    container.innerHTML = '<div class="loading">加载中...</div>';
    try {
        const response = await fetch(`${API_BASE}/tools/list?enabled_only=true`);
        const data = await response.json();
        if (!data.tools || data.tools.length === 0) {
            container.innerHTML = '<div style="color:#999; text-align:center;">暂无可用工具</div>';
            return;
        }
        let html = '<div style="display:grid; gap:15px;">';
        data.tools.forEach(tool => {
            const categoryEmoji = { weather: '🌤️', system: '💻', search: '🔍', file: '📁' };
            const emoji = categoryEmoji[tool.category] || '🔧';
            const statusColor = tool.enabled ? '#10b981' : '#9ca3af';
            const statusText = tool.enabled ? '启用' : '禁用';
            html += `
      <div style="background:white; padding:15px; border-radius:10px; border-left:4px solid ${statusColor};">
        <div style="display:flex; justify-content:space-between; align-items:start;">
          <div style="flex:1;">
            <div style="font-size:16px; font-weight:bold; color:#333; margin-bottom:5px;">${emoji} ${tool.name}</div>
            <div style="font-size:13px; color:#666; margin-bottom:10px;">${tool.description}</div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; font-size:12px;">
              <span style="background:#e0e7ff; color:#4f46e5; padding:3px 8px; border-radius:4px;">📦 ${tool.category}</span>
              <span style="background:${tool.enabled ? '#d1fae5' : '#f3f4f6'}; color:${statusColor}; padding:3px 8px; border-radius:4px;">● ${statusText}</span>
              ${tool.version ? `<span style="background:#fef3c7; color:#d97706; padding:3px 8px; border-radius:4px;">v${tool.version}</span>` : ''}
            </div>
          </div>
        </div>
        ${tool.parameters && tool.parameters.length > 0 ? `
          <div style="margin-top:10px; padding-top:10px; border-top:1px solid #e5e7eb;">
            <div style="font-size:12px; color:#666; margin-bottom:5px;">📝 参数:</div>
            <div style="display:flex; flex-wrap:wrap; gap:5px;">
              ${tool.parameters.map(p => `<span style=\"background:#f9fafb; border:1px solid #e5e7eb; padding:2px 6px; border-radius:3px; font-size:11px; color:#4b5563;\">${p.name}${p.required ? '*' : ''}: ${p.type}</span>`).join('')}
            </div>
          </div>` : ''}
      </div>`;
        });
        html += '</div>';
        container.innerHTML = html;
        const title = container.parentElement.querySelector('h4');
        if (title) title.innerHTML = `📋 可用工具 <span style="font-size:12px; color:#999; font-weight:normal;">(共 ${data.tools.length} 个)</span>`;
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

async function loadToolHistory() {
    const container = document.getElementById('toolHistory');
    if (!container) return;
    const limitSelect = document.getElementById('historyLimit');
    const limit = limitSelect ? limitSelect.value : 20;
    container.innerHTML = '<div class="loading">加载中...</div>';
    try {
        const response = await fetch(`${API_BASE}/tools/history?user_id=default_user&limit=${limit}`);
        const data = await response.json();
        if (!data.history || data.history.length === 0) {
            container.innerHTML = '<div style="color:#999; text-align:center;">暂无执行历史</div>';
            return;
        }
        let html = '<div style="display:grid; gap:10px;">';
        data.history.forEach(record => {
            const statusColor = record.success ? '#10b981' : '#ef4444';
            const statusIcon = record.success ? '✅' : '❌';
            const executionTime = record.execution_time ? record.execution_time.toFixed(3) : 'N/A';
            const date = new Date(record.executed_at);
            const timeStr = date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
            html += `
      <div style="background:white; padding:12px; border-radius:8px; border-left:3px solid ${statusColor};">
        <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:5px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:16px;">${statusIcon}</span>
            <span style="font-weight:bold; color:#333;">${record.tool_name}</span>
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="font-size:11px; color:#999;">${timeStr}</span>
            <span style="background:${statusColor}20; color:${statusColor}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:500;">${executionTime}s</span>
          </div>
        </div>
        ${record.error_message ? `<div style=\"margin-top:5px; padding:8px; background:#fef2f2; border-radius:5px; font-size:12px; color:#991b1b;\">⚠️ ${record.error_message}</div>` : ''}
      </div>`;
        });
        html += '</div>';
        container.innerHTML = html;
        const title = container.parentElement.querySelector('h4');
        if (title) title.innerHTML = `📊 工具执行历史 <span style="font-size:12px; color:#999; font-weight:normal;">(共 ${data.total} 条)</span>`;
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

export { initTools, loadTools, loadToolHistory };
