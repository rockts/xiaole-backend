// documents.js - 文档总结与管理模块
// 负责：上传、列表加载、查看、导出、删除、总结展示；统一事件委托

let documentsInitialized = false;

// 模块内部状态（目前无需复杂状态）

function initDocuments() {
    if (documentsInitialized) return;
    documentsInitialized = true;

    // 文件上传 input 监听
    const fileInput = document.getElementById('documentFileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleDocumentUpload);
    }

    // 上传按钮（选择文件）与刷新按钮、动态文档操作事件委托
    const documentsTab = document.getElementById('documents');
    if (documentsTab) {
        documentsTab.addEventListener('click', (e) => {
            const target = e.target.closest('[data-action]');
            if (!target) return;
            const action = target.getAttribute('data-action');
            switch (action) {
                case 'document-file-select':
                    triggerDocumentFileSelect();
                    break;
                case 'documents-refresh':
                    loadDocuments();
                    break;
                case 'document-view': {
                    const docId = target.getAttribute('data-doc-id');
                    if (docId) viewDocumentSummary(docId);
                    break;
                }
                case 'document-export': {
                    const docId = target.getAttribute('data-doc-id');
                    if (docId) exportDocumentSummary(docId);
                    break;
                }
                case 'document-delete': {
                    const docId = target.getAttribute('data-doc-id');
                    if (docId) deleteDocument(docId);
                    break;
                }
                default:
                    break;
            }
        });
    }
}

function triggerDocumentFileSelect() {
    const fileInput = document.getElementById('documentFileInput');
    if (fileInput) fileInput.click();
}

async function handleDocumentUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const allowedTypes = ['.pdf', '.docx', '.txt', '.md'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedTypes.includes(fileExt)) {
        showNotification('❌ 不支持的文件类型！仅支持 PDF, DOCX, TXT, MD', 'error');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showNotification('❌ 文件过大！最大支持 10MB', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        showNotification('⏳ 上传并分析中...', 'info');
        const userId = 'default_user';
        const response = await fetch(`${API_BASE}/api/users/${userId}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            showNotification('✅ 上传成功，正在生成总结', 'success');
            if (data.document) showDocumentSummary(data.document);
            loadDocuments();
        } else {
            showNotification(`❌ ${data.error || '上传失败'}`, 'error');
        }
    } catch (error) {
        console.error('上传文档失败:', error);
        showNotification('❌ 上传失败，请检查网络', 'error');
    }

    // 清空 input
    event.target.value = '';
}

async function loadDocuments() {
    const container = document.getElementById('documentsList');
    if (!container) return;
    container.innerHTML = '<div class="loading">加载中...</div>';
    try {
        const userId = 'default_user';
        const response = await fetch(`${API_BASE}/api/users/${userId}/documents?limit=50`);
        const data = await response.json();
        if (data.success && data.documents.length > 0) {
            let html = '<div style="display: grid; gap: 15px;">';
            data.documents.forEach(doc => {
                const statusColor = {
                    'completed': '#10b981',
                    'processing': '#3b82f6',
                    'failed': '#ef4444',
                    'pending': '#f59e0b'
                }[doc.status] || '#6b7280';
                const statusText = {
                    'completed': '✅ 已完成',
                    'processing': '⚡ 处理中',
                    'failed': '❌ 失败',
                    'pending': '⏳ 待处理'
                }[doc.status] || doc.status;
                html += `
                <div style="background: white; padding: 15px; border-radius: 10px; border: 1px solid #e5e7eb;">
                  <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div style="flex: 1;">
                      <div style="font-weight: bold; color: #1f2937; margin-bottom: 5px;">📄 ${escapeHtml(doc.original_filename)}</div>
                      <div style="font-size: 12px; color: #6b7280;">${doc.file_type.toUpperCase()} · ${(doc.file_size / 1024).toFixed(1)} KB · ${new Date(doc.created_at).toLocaleString('zh-CN')}</div>
                    </div>
                    <div style="background: ${statusColor}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; white-space: nowrap;">${statusText}</div>
                  </div>
                  ${doc.summary ? `
                    <div style="background: #f9fafb; padding: 10px; border-radius: 6px; margin: 10px 0; font-size: 13px; color: #374151; line-height: 1.6;">
                      ${escapeHtml(doc.summary.substring(0, 200))}${doc.summary.length > 200 ? '...' : ''}
                    </div>
                  ` : ''}
                  <div style="display: flex; gap: 10px; margin-top: 10px;">
                    ${doc.status === 'completed' ? `
                      <button data-action="document-view" data-doc-id="${doc.id}" style="padding: 6px 12px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px;">🔍 查看详情</button>
                      <button data-action="document-export" data-doc-id="${doc.id}" style="padding: 6px 12px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px;">💾 导出</button>
                    ` : ''}
                    <button data-action="document-delete" data-doc-id="${doc.id}" style="padding: 6px 12px; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px;">🗑️ 删除</button>
                  </div>
                </div>`;
            });
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #6b7280;">📭 还没有上传任何文档</div>';
        }
    } catch (error) {
        console.error('加载文档列表失败:', error);
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #ef4444;">❌ 加载失败</div>';
    }
}

async function viewDocumentSummary(docId) {
    try {
        const response = await fetch(`${API_BASE}/api/documents/${docId}`);
        const data = await response.json();
        if (data.success) {
            showDocumentSummary(data.document);
        } else {
            showNotification(`❌ 获取文档失败: ${data.error || '未知错误'}`, 'error');
        }
    } catch (error) {
        console.error('获取文档失败:', error);
        showNotification(`❌ 获取文档失败: ${error.message}`, 'error');
    }
}

function showDocumentSummary(doc) {
    let keyPoints = [];
    try {
        if (typeof doc.key_points === 'string') keyPoints = JSON.parse(doc.key_points);
        else if (Array.isArray(doc.key_points)) keyPoints = doc.key_points;
    } catch (e) {
        console.error('解析key_points失败:', e);
    }
    let html = `
      <div style="max-width: 700px;">
        <h3>📄 ${escapeHtml(doc.original_filename)}</h3>
        <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 15px 0;">
          <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 13px;">
            <div><strong>文件类型:</strong> ${doc.file_type.toUpperCase()}</div>
            <div><strong>文件大小:</strong> ${(doc.file_size / 1024).toFixed(1)} KB</div>
            <div><strong>原文长度:</strong> ${doc.content_length || 0} 字</div>
            <div><strong>总结长度:</strong> ${doc.summary_length || 0} 字</div>
            <div><strong>分块数:</strong> ${doc.chunk_count || 1}</div>
            <div><strong>处理时间:</strong> ${doc.processing_time ? doc.processing_time.toFixed(2) + '秒' : 'N/A'}</div>
          </div>
        </div>
        ${keyPoints.length > 0 ? `
          <div style="margin: 20px 0;">
            <h4 style="color: #667eea; margin-bottom: 10px;">✨ 关键要点</h4>
            <ul style="background: #f9fafb; padding: 15px 15px 15px 35px; border-radius: 8px; line-height: 1.8; margin: 0;">
              ${keyPoints.map(point => `<li>${escapeHtml(point)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        <div style="margin: 20px 0;">
          <h4 style="color: #667eea; margin-bottom: 10px;">📝 智能总结</h4>
          <div class="markdown-content" style="background: #f9fafb; padding: 25px 30px; border-radius: 8px; line-height: 1.8; color: #374151;">
            ${marked.parse(doc.summary || '总结生成中...')}
          </div>
        </div>
      </div>`;
    showCustomNotification('文档总结', html);
    setTimeout(() => {
        const markdownContent = document.querySelector('.custom-notification .markdown-content');
        if (!markdownContent) return;
        markdownContent.querySelectorAll('h1, h2, h3, h4').forEach(h => {
            h.style.color = '#1f2937';
            h.style.marginTop = '16px';
            h.style.marginBottom = '8px';
            h.style.fontWeight = 'bold';
        });
        markdownContent.querySelectorAll('ol, ul').forEach(list => {
            list.style.marginLeft = '20px';
            list.style.marginTop = '8px';
            list.style.marginBottom = '8px';
        });
        markdownContent.querySelectorAll('li').forEach(li => {
            li.style.marginBottom = '4px';
        });
        markdownContent.querySelectorAll('p').forEach(p => {
            p.style.marginBottom = '12px';
        });
        markdownContent.querySelectorAll('strong').forEach(strong => {
            strong.style.color = '#374151';
            strong.style.fontWeight = '600';
        });
    }, 100);
}

async function exportDocumentSummary(docId) {
    try {
        window.open(`${API_BASE}/api/documents/${docId}/export?format=md`, '_blank');
        showNotification('✅ 正在下载...', 'success');
    } catch (error) {
        console.error('导出失败:', error);
        showNotification('❌ 导出失败', 'error');
    }
}

async function deleteDocument(docId) {
    if (!confirm('确定要删除这个文档吗？')) return;
    try {
        const response = await fetch(`${API_BASE}/api/documents/${docId}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            showNotification('✅ 文档已删除', 'success');
            loadDocuments();
        } else {
            showNotification('❌ 删除失败', 'error');
        }
    } catch (error) {
        console.error('删除文档失败:', error);
        showNotification('❌ 删除失败', 'error');
    }
}

export {
    initDocuments,
    handleDocumentUpload,
    loadDocuments,
    viewDocumentSummary,
    exportDocumentSummary,
    deleteDocument
};
