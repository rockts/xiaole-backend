let uploadedImagePath = null;
let editingMessage = null;
let editingImagePath = null;
let originalContent = '';

export function initComposer() {
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keydown', handleMessageKeyDown);
    }

    const homeInput = document.getElementById('homeMessageInput');
    if (homeInput) {
        homeInput.addEventListener('keydown', handleHomeInputKeyDown);
    }

    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessageFromDiv);
    }

    const homeSendBtn = document.getElementById('homeSendBtn');
    if (homeSendBtn) {
        homeSendBtn.addEventListener('click', sendHomeMessage);
    }

    const imageUploadInput = document.getElementById('imageUpload');
    if (imageUploadInput) {
        imageUploadInput.addEventListener('change', handleImageUpload);
        imageUploadInput.addEventListener('cancel', () => console.log('❌ 用户取消了文件选择'));
    }

    document.querySelectorAll('[data-trigger="upload"]').forEach((btn) => {
        btn.addEventListener('click', triggerImageUpload);
    });

    document.querySelectorAll('[data-action="voice"]').forEach((btn) => {
        btn.addEventListener('click', toggleVoiceInput);
    });

    const chatInput = document.getElementById('messageInput');
    if (chatInput) {
        chatInput.addEventListener('focus', () => {
            const hintsBar = document.getElementById('shortcutHints');
            if (hintsBar) hintsBar.style.opacity = '1';
        });
    }

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const modal = document.getElementById('imageViewerModal');
            if (modal && modal.classList.contains('active')) {
                modal.classList.remove('active');
                document.body.style.overflow = '';
            }
        }
    });
}

export function sendMessageFromDiv() {
    const input = document.getElementById('messageInput');
    if (!input) return;
    const message = input.textContent.trim();

    if (!message && !uploadedImagePath) return;

    const actualMessage = message || '请详细描述这张图片的内容';

    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) sendBtn.disabled = true;
    input.contentEditable = 'false';

    if (editingMessage) {
        let nextElement = editingMessage.nextElementSibling;
        if (nextElement && nextElement.classList.contains('assistant')) {
            nextElement.remove();
        }
        editingMessage.remove();
        clearEditingState();
    }

    let displayMessage = message || '识别图片';
    addMessage('user', displayMessage, null, uploadedImagePath);
    input.textContent = '';

    const currentImagePath = uploadedImagePath;
    removeImagePreview();

    sendChatRequest(actualMessage, currentImagePath).finally(() => {
        if (sendBtn) sendBtn.disabled = false;
        input.contentEditable = 'true';
        input.focus();
    });
}

export function sendHomeMessage() {
    const homeInput = document.getElementById('homeMessageInput');
    const mainInput = document.getElementById('messageInput');
    const homeHero = document.getElementById('homeHero');
    const homePanel = document.querySelector('#homeHero .home-panel');
    const chatTab = document.getElementById('chat');
    const chatInputBar = document.getElementById('chatInputBar');
    if (!homeInput || !mainInput) return;

    const text = homeInput.textContent.trim();
    if (!text && !uploadedImagePath) {
        mainInput.focus();
        return;
    }

    mainInput.textContent = text;
    homeInput.textContent = '';

    if (chatTab) {
        chatTab.classList.add('active');
        chatTab.style.display = 'flex';
    }
    if (homePanel) homePanel.style.display = 'none';
    if (homeHero) homeHero.style.display = 'none';
    if (chatInputBar) chatInputBar.style.display = 'block';

    sendMessageFromDiv();
}

export function triggerImageUpload() {
    const uploadInput = document.getElementById('imageUpload');
    if (uploadInput) {
        uploadInput.click();
    }
}

export async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showNotification('❌ 不支持的图片格式', 'error');
        return;
    }

    if (file.size > 20 * 1024 * 1024) {
        showNotification('❌ 文件过大（最大20MB）', 'error');
        return;
    }

    showNotification('📤 正在上传图片...', 'info');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/vision/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            uploadedImagePath = result.file_path;
            showNotification('✅ 图片上传成功', 'success');
            showImagePreview(file, result.file_path);
        } else {
            showNotification(`❌ 上传失败: ${result.error}`, 'error');
        }
    } catch (error) {
        showNotification('❌ 上传失败: 网络错误', 'error');
    }
}

export function showImagePreview(file, filePath) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const previewHtml = `
            <div class="image-preview" id="imagePreview">
                <div class="image-preview-header">
                    <span>📷 已上传图片</span>
                    <button data-action="remove-preview" class="remove-btn">✕</button>
                </div>
                <img src="${e.target.result}" alt="预览图" style="max-width: 200px; max-height: 200px; border-radius: 8px;">
                <div class="image-preview-actions">
                    <div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
                        💡 输入问题后点击发送，或直接发送识别图片内容
                    </div>
                </div>
            </div>
        `;

        const inputContainer = document.querySelector('.input-container');
        const existing = document.getElementById('imagePreview');
        if (existing) existing.remove();
        if (inputContainer) inputContainer.insertAdjacentHTML('beforebegin', previewHtml);

        const removeBtn = document.querySelector('[data-action="remove-preview"]');
        if (removeBtn) {
            removeBtn.addEventListener('click', removeImagePreview);
        }
    };
    reader.readAsDataURL(file);
}

export function removeImagePreview() {
    const preview = document.getElementById('imagePreview');
    if (preview) preview.remove();
    uploadedImagePath = null;
    const fileInput = document.getElementById('imageUpload');
    if (fileInput) {
        fileInput.value = '';
    }
}

export function showImagePreviewInInput(imagePath) {
    const previewHtml = `
        <div class="image-preview" id="imagePreview">
            <div class="image-preview-header">
                <span>📷 原消息图片</span>
                <button data-action="remove-preview" class="remove-btn">✕</button>
            </div>
            <img src="/${imagePath}" alt="预览图" style="max-width: 200px; max-height: 200px; border-radius: 8px;">
            <div class="image-preview-actions">
                <div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
                    💡 编辑消息时保留原图片
                </div>
            </div>
        </div>
    `;

    const inputContainer = document.querySelector('.input-container');
    const existing = document.getElementById('imagePreview');
    if (existing) existing.remove();
    if (inputContainer) inputContainer.insertAdjacentHTML('beforebegin', previewHtml);

    uploadedImagePath = imagePath;

    const removeBtn = document.querySelector('[data-action="remove-preview"]');
    if (removeBtn) {
        removeBtn.addEventListener('click', removeImagePreview);
    }
}

export function editMessage(messageDiv, content, imagePath = null) {
    const input = document.getElementById('messageInput');
    if (!input) return;

    editingMessage = messageDiv;
    originalContent = input.textContent;
    editingImagePath = imagePath;

    input.textContent = content;
    input.focus();

    if (imagePath) {
        showImagePreviewInInput(imagePath);
    }

    showEditingIndicator();
}

export function showEditingIndicator() {
    const existing = document.querySelector('.editing-indicator');
    if (existing) existing.remove();

    const indicator = document.createElement('div');
    indicator.className = 'editing-indicator';
    indicator.innerHTML = `
        <span>✏️ 正在编辑消息</span>
        <button type="button" data-action="cancel-edit">取消</button>
    `;
    document.body.appendChild(indicator);

    const cancelBtn = indicator.querySelector('[data-action="cancel-edit"]');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', clearEditingState);
    }
}

export function clearEditingState() {
    editingMessage = null;
    editingImagePath = null;
    originalContent = '';

    const indicator = document.querySelector('.editing-indicator');
    if (indicator) indicator.remove();
}

function handleMessageKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessageFromDiv();
    }
}

function handleHomeInputKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendHomeMessage();
    }
}

async function sendChatRequest(message, imagePath) {
    try {
        const settings = getSettings();
        const responseStyle = settings.responseStyle || 'balanced';

        const memorizeKeywords = ['记住', '保存', '记下', '存一下', '记录'];
        const shouldMemorize = message && memorizeKeywords.some((kw) => message.includes(kw));

        let url = `${API_BASE}/chat?prompt=${encodeURIComponent(message || '')}&response_style=${responseStyle}`;

        if (currentSessionId) {
            url += `&session_id=${currentSessionId}`;
        }

        if (imagePath) {
            url += `&image_path=${encodeURIComponent(imagePath)}`;
        }

        if (shouldMemorize) {
            url += `&memorize=true`;
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);

        const response = await fetch(url, {
            method: 'POST',
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        const data = await response.json();

        if (response.ok) {
            currentSessionId = data.session_id;
            addMessage('assistant', data.reply);
        } else {
            addMessage('assistant', '抱歉，出现错误：' + (data.detail || '未知错误'));
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            addMessage('assistant', '请求超时，问题可能比较复杂，请稍后再试。');
        } else {
            addMessage('assistant', '网络错误：' + error.message);
        }
    }
}

function showNotification(message, type) {
    if (window.showNotification) {
        window.showNotification(message, type);
    }
}

function getSettings() {
    return window.getSettings ? window.getSettings() : {};
}
