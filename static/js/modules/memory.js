/**
 * memory.js
 * 记忆管理模块：搜索、加载、编辑、删除记忆
 */

export function initMemory() {
    // 绑定搜索按钮
    const searchBtn = document.querySelector('[data-action="search-memories"]');
    if (searchBtn) {
        searchBtn.addEventListener('click', searchMemories);
    }

    const semanticBtn = document.querySelector('[data-action="semantic-search"]');
    if (semanticBtn) {
        semanticBtn.addEventListener('click', semanticSearch);
    }

    const loadAllBtn = document.querySelector('[data-action="load-memories"]');
    if (loadAllBtn) {
        loadAllBtn.addEventListener('click', loadRecentMemories);
    }

    // 绑定搜索输入框回车
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchMemories();
            }
        });
    }
}

export async function loadMemoryStats() {
    try {
        const response = await fetch(`${window.API_BASE}/memory/stats`);
        const data = await response.json();

        const statsGrid = document.getElementById('statsGrid');
        const tags = data.by_tag || {};

        statsGrid.innerHTML = `
            <div class="stat-item">
                <div class="stat-number">${data.total}</div>
                <div class="stat-label">总记忆数</div>
            </div>
            ${Object.entries(tags).map(([tag, count]) => `
                <div class="stat-item">
                    <div class="stat-number">${count}</div>
                    <div class="stat-label">${tag}</div>
                </div>
            `).join('')}
        `;

        loadRecentMemories();
    } catch (error) {
        document.getElementById('statsGrid').innerHTML =
            `<div class="error">加载失败: ${error.message}</div>`;
    }
}

export async function loadRecentMemories() {
    const container = document.getElementById('memoryList');
    if (!container) return;

    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const response = await fetch(`${window.API_BASE}/memory/recent?hours=24&limit=20`);
        const data = await response.json();

        const memories = data.memory || data.memories || [];

        if (memories.length > 0) {
            container.innerHTML = memories.map(mem => createMemoryItemHTML(mem)).join('');
            bindMemoryActions(container);
        } else {
            container.innerHTML = '<div class="loading">没有记忆记录</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

export async function searchMemories() {
    const keywords = document.getElementById('searchInput')?.value.trim();
    if (!keywords) {
        loadRecentMemories();
        return;
    }

    const container = document.getElementById('memoryList');
    if (!container) return;

    container.innerHTML = '<div class="loading">关键词搜索中...</div>';

    try {
        const response = await fetch(
            `${window.API_BASE}/memory/search?keywords=${encodeURIComponent(keywords)}&limit=20`
        );
        const data = await response.json();

        if (data.memories && data.memories.length > 0) {
            container.innerHTML = data.memories.map(mem => createMemoryItemHTML(mem)).join('');
            bindMemoryActions(container);
        } else {
            container.innerHTML = '<div class="loading">没有找到相关记忆</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="error">搜索失败: ${error.message}</div>`;
    }
}

export async function semanticSearch() {
    const query = document.getElementById('searchInput')?.value.trim();
    if (!query) {
        alert('请输入查询内容');
        return;
    }

    const container = document.getElementById('memoryList');
    if (!container) return;

    container.innerHTML = '<div class="loading">🧠 语义搜索中...</div>';

    try {
        const response = await fetch(
            `${window.API_BASE}/memory/semantic?query=${encodeURIComponent(query)}&limit=20`
        );
        const data = await response.json();

        if (data.memories && data.memories.length > 0) {
            container.innerHTML = data.memories.map(mem => createMemoryItemHTML(mem, true)).join('');
            bindMemoryActions(container);
        } else {
            container.innerHTML = '<div class="loading">没有找到相关记忆</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="error">搜索失败: ${error.message}</div>`;
    }
}

export async function editMemory(memoryId, currentTag) {
    const contentEl = document.getElementById(`content-${memoryId}`);
    if (!contentEl) return;

    const currentContent = contentEl.textContent;

    const newContent = prompt('编辑记忆内容:', currentContent);
    if (newContent === null || newContent.trim() === '') {
        return;
    }

    const newTag = prompt('编辑标签 (facts/image/conversation/schedule等):', currentTag);
    if (newTag === null || newTag.trim() === '') {
        return;
    }

    try {
        const response = await fetch(`${window.API_BASE}/api/memory/${memoryId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: newContent.trim(),
                tag: newTag.trim()
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('✅ 记忆更新成功', 'success');
            loadRecentMemories();
        } else {
            showNotification('❌ 更新失败: ' + (data.error || '未知错误'), 'error');
        }
    } catch (error) {
        showNotification('❌ 更新失败: 网络错误', 'error');
    }
}

export async function deleteMemory(memoryId) {
    if (!confirm('确定要删除这条记忆吗？此操作不可恢复！')) {
        return;
    }

    try {
        const response = await fetch(`${window.API_BASE}/api/memory/${memoryId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showNotification('✅ 记忆已删除', 'success');
            const memoryEl = document.getElementById(`memory-${memoryId}`);
            if (memoryEl) {
                memoryEl.style.opacity = '0';
                setTimeout(() => memoryEl.remove(), 300);
            }
        } else {
            showNotification('❌ 删除失败: ' + (data.error || '未知错误'), 'error');
        }
    } catch (error) {
        showNotification('❌ 删除失败: 网络错误', 'error');
    }
}

// Helper functions
function createMemoryItemHTML(mem, showScore = false) {
    const scoreHTML = showScore && mem.score
        ? `<span>📊 相似度: ${(mem.score * 100).toFixed(1)}%</span>`
        : '';

    return `
        <div class="memory-item" id="memory-${mem.id}">
            <div class="memory-content" id="content-${mem.id}">${window.marked?.parse(mem.content) || mem.content}</div>
            <div class="memory-meta">
                <span>🏷️ ${mem.tag}</span>
                <span>🕐 ${mem.timestamp}</span>
                ${scoreHTML}
            </div>
            <div class="memory-actions" style="margin-top: 10px; display: flex; gap: 8px;">
                <button data-memory-id="${mem.id}" data-memory-tag="${mem.tag}" class="edit-memory-btn"
                    style="padding: 5px 12px; background: #667eea; color: white; 
                           border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">
                    ✏️ 编辑
                </button>
                <button data-memory-id="${mem.id}" class="delete-memory-btn"
                    style="padding: 5px 12px; background: #f56565; color: white; 
                           border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">
                    🗑️ 删除
                </button>
            </div>
        </div>
    `;
}

function bindMemoryActions(container) {
    const editButtons = container.querySelectorAll('.edit-memory-btn');
    const deleteButtons = container.querySelectorAll('.delete-memory-btn');

    editButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            editMemory(this.dataset.memoryId, this.dataset.memoryTag);
        });
    });

    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            deleteMemory(this.dataset.memoryId);
        });
    });
}

function showNotification(message, type) {
    if (window.showNotification) {
        window.showNotification(message, type);
    } else {
        console.log(`[${type}] ${message}`);
    }
}
