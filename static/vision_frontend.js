/**
 * 图片上传和识别功能 - v0.6.0 Phase 4
 * 添加到 static/index.html 的 JavaScript 部分
 */

// ========================================
// 图片上传功能
// ========================================

let uploadedImagePath = null;

/**
 * 处理图片上传
 */
async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 验证文件类型
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showNotification('❌ 不支持的图片格式', 'error');
        return;
    }

    // 验证文件大小 (20MB)
    if (file.size > 20 * 1024 * 1024) {
        showNotification('❌ 文件过大（最大20MB）', 'error');
        return;
    }

    // 显示上传中状态
    showNotification('📤 正在上传图片...', 'info');

    try {
        // 创建FormData
        const formData = new FormData();
        formData.append('file', file);

        // 上传图片
        const response = await fetch('/api/vision/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            uploadedImagePath = result.file_path;
            showNotification('✅ 图片上传成功', 'success');

            // 显示图片预览
            showImagePreview(file, result.file_path);
        } else {
            showNotification(`❌ 上传失败: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showNotification('❌ 上传失败: 网络错误', 'error');
    }
}

/**
 * 显示图片预览
 */
function showImagePreview(file, filePath) {
    const reader = new FileReader();
    reader.onload = (e) => {
        // 创建预览容器
        const previewHtml = `
            <div class="image-preview" id="imagePreview">
                <div class="image-preview-header">
                    <span>📷 已上传图片</span>
                    <button onclick="removeImagePreview()" class="remove-btn">✕</button>
                </div>
                <img src="${e.target.result}" alt="预览图" style="max-width: 200px; max-height: 200px; border-radius: 8px;">
                <div class="image-preview-actions">
                    <button onclick="analyzeUploadedImage()" class="analyze-btn">🔍 识别图片</button>
                </div>
            </div>
        `;

        // 插入到输入框上方
        const inputContainer = document.querySelector('.input-container');
        const existing = document.getElementById('imagePreview');
        if (existing) {
            existing.remove();
        }
        inputContainer.insertAdjacentHTML('beforebegin', previewHtml);
    };
    reader.readAsDataURL(file);
}

/**
 * 移除图片预览
 */
function removeImagePreview() {
    const preview = document.getElementById('imagePreview');
    if (preview) {
        preview.remove();
    }
    uploadedImagePath = null;
    // 重置文件输入
    const fileInput = document.getElementById('imageUpload');
    if (fileInput) {
        fileInput.value = '';
    }
}

/**
 * 分析上传的图片
 */
async function analyzeUploadedImage() {
    if (!uploadedImagePath) {
        showNotification('❌ 没有上传图片', 'error');
        return;
    }

    showNotification('🔍 正在分析图片...', 'info');

    try {
        const response = await fetch('/api/vision/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image_path: uploadedImagePath,
                prompt: '请详细描述这张图片的内容'
            })
        });

        const result = await response.json();

        if (result.success) {
            // 在聊天中显示分析结果
            addMessage('assistant', `📷 **图片分析结果：**\n\n${result.description}\n\n_使用模型: ${result.model}_`);
            showNotification('✅ 图片识别完成', 'success');
        } else {
            showNotification(`❌ 识别失败: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Analyze error:', error);
        showNotification('❌ 识别失败: 网络错误', 'error');
    }
}

/**
 * 触发图片上传
 */
function triggerImageUpload() {
    document.getElementById('imageUpload').click();
}

// ========================================
// CSS样式（添加到<style>标签中）
// ========================================
const visionStyles = `
    /* 图片上传按钮 */
    .upload-image-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.3s;
        margin-right: 8px;
    }

    .upload-image-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }

    /* 图片预览容器 */
    .image-preview {
        background: var(--card-bg);
        border: 2px solid var(--border-color);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .image-preview-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 14px;
        color: var(--text-primary);
        font-weight: 500;
    }

    .remove-btn {
        background: #ff4444;
        color: white;
        border: none;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
    }

    .remove-btn:hover {
        background: #cc0000;
        transform: scale(1.1);
    }

    .image-preview-actions {
        display: flex;
        gap: 8px;
    }

    .analyze-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 13px;
        transition: all 0.3s;
        flex: 1;
    }

    .analyze-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
`;

// ========================================
// HTML元素（添加到输入区域）
// ========================================
const visionHTML = `
    <!-- 图片上传输入（隐藏） -->
    <input type="file" id="imageUpload" accept="image/*" style="display: none;" onchange="handleImageUpload(event)">
    
    <!-- 在发送按钮前添加上传按钮 -->
    <button onclick="triggerImageUpload()" class="upload-image-btn" title="上传图片">📷 图片</button>
`;

console.log('📷 Vision Tool 前端组件已准备');
console.log('请手动添加以下元素到HTML:');
console.log('1. 将 visionStyles 添加到 <style> 标签');
console.log('2. 将 visionHTML 添加到 input-container');
