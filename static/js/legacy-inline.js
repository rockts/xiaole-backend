let currentSessionId = null;
const API_BASE = '';
window.API_BASE = API_BASE;  // 暴露给模块使用

// 主题切换功能
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    const themeIcon = document.getElementById('themeIcon');

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // 更新图标
    themeIcon.textContent = newTheme === 'dark' ? '☀️' : '🌙';
}

// 初始化主题
function initTheme() {
    const html = document.documentElement;
    const themeIcon = document.getElementById('themeIcon');

    // 检查用户偏好
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    // 确定使用的主题
    const theme = savedTheme || (systemPrefersDark ? 'dark' : 'light');

    html.setAttribute('data-theme', theme);
    if (themeIcon) {
        themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
}

// 页面加载时初始化主题
document.addEventListener('DOMContentLoaded', initTheme);

// ===== 设置管理功能 v0.6.0 =====

// 设置项默认值
const DEFAULT_SETTINGS = {
    themePreference: 'system',
    keyboardShortcuts: true,
    shortcutHintsEnabled: true,
    responseStyle: 'balanced',
    proactiveQA: true
};

// 初始化设置
function initSettings() {
    const settings = getSettings();

    // 应用所有设置
    document.getElementById('themePreference').value = settings.themePreference;
    document.getElementById('keyboardShortcuts').checked = settings.keyboardShortcuts;
    document.getElementById('shortcutHintsEnabled').checked = settings.shortcutHintsEnabled;
    document.getElementById('responseStyle').value = settings.responseStyle;
    document.getElementById('proactiveQA').checked = settings.proactiveQA;

    // 应用主题偏好
    applyThemePreference(settings.themePreference);

    // 应用快捷键提示
    if (settings.shortcutHintsEnabled) {
        showShortcutHints();
    }

    // 初始化语音设置 v0.8.0
    initVoiceSettings();
}

// 获取设置
function getSettings() {
    const saved = localStorage.getItem('userSettings');
    return saved ? JSON.parse(saved) : DEFAULT_SETTINGS;
}

// 保存设置
function saveSettings(settings) {
    localStorage.setItem('userSettings', JSON.stringify(settings));
}

// 更新主题偏好
function updateThemePreference(value) {
    const settings = getSettings();
    settings.themePreference = value;
    saveSettings(settings);
    applyThemePreference(value);
    showToast(`✅ 主题偏好已设置为：${getThemeLabel(value)}`, 'success');
}

// 应用主题偏好
function applyThemePreference(preference) {
    const html = document.documentElement;
    const themeIcon = document.getElementById('themeIcon');

    if (preference === 'system') {
        // 跟随系统
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = systemPrefersDark ? 'dark' : 'light';
        html.setAttribute('data-theme', theme);
        if (themeIcon) {
            themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    } else {
        // 固定主题
        html.setAttribute('data-theme', preference);
        if (themeIcon) {
            themeIcon.textContent = preference === 'dark' ? '☀️' : '🌙';
        }
        localStorage.setItem('theme', preference);
    }
}

// 获取主题标签
function getThemeLabel(value) {
    const labels = {
        'system': '跟随系统',
        'light': '始终亮色',
        'dark': '始终暗色'
    };
    return labels[value] || value;
}

// 切换快捷键功能
function toggleKeyboardShortcuts(enabled) {
    const settings = getSettings();
    settings.keyboardShortcuts = enabled;
    saveSettings(settings);
    showToast(enabled ? '✅ 快捷键已启用' : '⚠️ 快捷键已禁用', enabled ? 'success' : 'warning');
}

// 切换快捷键提示栏
function toggleShortcutHints(enabled) {
    const settings = getSettings();
    settings.shortcutHintsEnabled = enabled;
    saveSettings(settings);

    const hints = document.getElementById('shortcutHints');
    if (enabled) {
        showShortcutHints();
    } else {
        hints.style.opacity = '0';
        setTimeout(() => {
            hints.style.display = 'none';
        }, 300);
    }
    showToast(enabled ? '✅ 快捷键提示已显示' : '⚠️ 快捷键提示已隐藏', enabled ? 'success' : 'warning');
}

// 更新AI响应风格
function updateResponseStyle(style) {
    const settings = getSettings();
    settings.responseStyle = style;
    saveSettings(settings);

    const labels = {
        'concise': '简洁模式',
        'balanced': '平衡模式',
        'detailed': '详细模式',
        'professional': '专业模式'
    };
    showToast(`✅ AI响应风格已设置为：${labels[style]}`, 'success');
}

// 切换主动问答
function toggleProactiveQA(enabled) {
    const settings = getSettings();
    settings.proactiveQA = enabled;
    saveSettings(settings);
    showToast(enabled ? '✅ 主动问答提示已启用' : '⚠️ 主动问答提示已禁用', enabled ? 'success' : 'warning');
}

// ==================== v0.8.0 语音设置功能 ====================

// 更新语音服务提供商
function updateVoiceProvider(provider) {
    localStorage.setItem('useBaiduVoice', provider === 'baidu');
    const providerName = provider === 'baidu' ? '百度语音' : 'Google语音';
    showToast(`✅ 已切换到${providerName}识别`, 'success');
}

// 更新TTS提供商
function updateTTSProvider(provider) {
    localStorage.setItem('ttsProvider', provider);
    const ttsName = provider === 'baidu' ? '百度语音合成' : '浏览器语音合成';
    showToast(`✅ 已切换到${ttsName}`, 'success');

    // 显示/隐藏百度TTS音色选择
    const personSetting = document.getElementById('baiduTTSPersonSetting');
    if (personSetting) {
        personSetting.style.display = provider === 'baidu' ? 'flex' : 'none';
    }
}

// 更新TTS音色
function updateTTSPerson(person) {
    localStorage.setItem('ttsPerson', person);
    const personNames = {
        '0': '度小美（女声，温柔）',
        '1': '度小宇（男声，温和）',
        '3': '度逍遥（男声，年轻活力）',
        '4': '度丫丫（女声，活泼可爱）'
    };
    showToast(`✅ 音色已设置为：${personNames[person] || '度小美'}`, 'success');
}

// 更新语音自动播放设置
function updateVoiceAutoPlay(enabled) {
    localStorage.setItem('voiceAutoPlay', enabled);
    showToast(enabled ? '✅ 已开启语音自动播放' : '❌ 已关闭语音自动播放', 'info');
}

// 更新语速
function updateVoiceRate(value) {
    localStorage.setItem('voiceRate', value);
    document.getElementById('voiceRateValue').textContent = value + 'x';
}

// 更新音量
function updateVoiceVolume(value) {
    localStorage.setItem('voiceVolume', value);
    const percentage = Math.round(value * 100);
    document.getElementById('voiceVolumeValue').textContent = percentage + '%';
}

// 初始化语音设置
function initVoiceSettings() {
    // 首次访问时默认使用百度语音（国内更稳定）
    if (localStorage.getItem('useBaiduVoice') === null) {
        localStorage.setItem('useBaiduVoice', 'true');
    }

    const useBaiduVoice = localStorage.getItem('useBaiduVoice') === 'true';
    const ttsProvider = localStorage.getItem('ttsProvider') || 'web';
    const ttsPerson = localStorage.getItem('ttsPerson') || '0'; // 默认度小美(女声)
    const autoPlay = localStorage.getItem('voiceAutoPlay') === 'true';
    const rate = localStorage.getItem('voiceRate') || '1.0';
    const volume = localStorage.getItem('voiceVolume') || '1.0';

    document.getElementById('voiceProvider').value = useBaiduVoice ? 'baidu' : 'google';
    document.getElementById('ttsProvider').value = ttsProvider;
    document.getElementById('ttsPerson').value = ttsPerson;
    document.getElementById('voiceAutoPlay').checked = autoPlay;
    document.getElementById('voiceRate').value = rate;
    document.getElementById('voiceRateValue').textContent = rate + 'x';
    document.getElementById('voiceVolume').value = volume;
    document.getElementById('voiceVolumeValue').textContent = Math.round(volume * 100) + '%';

    // 显示/隐藏百度TTS音色选择
    const personSetting = document.getElementById('baiduTTSPersonSetting');
    if (personSetting) {
        personSetting.style.display = ttsProvider === 'baidu' ? 'flex' : 'none';
    }
}

// ==================== 设置管理功能 ====================

// 重置所有设置
function resetSettings() {
    if (confirm('确定要重置所有设置为默认值吗？')) {
        localStorage.removeItem('userSettings');
        localStorage.removeItem('theme');
        initSettings();
        applyThemePreference('system');
        showToast('✅ 所有设置已重置为默认值', 'success');
    }
}

// 页面加载时初始化设置
document.addEventListener('DOMContentLoaded', function () {
    initSettings();
});

// 切换标签页
function switchTab(tabName, event) {
    // 移除所有tab和nav-item的active状态
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // 激活对应的nav-item（侧边栏）
    const navItem = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (navItem) {
        navItem.classList.add('active');
    }

    // 激活对应的tab按钮（兼容旧的tabs）
    if (event && event.target && event.target.classList.contains('tab')) {
        event.target.classList.add('active');
    } else {
        const tabButton = document.querySelector(`.tab[onclick*="${tabName}"]`);
        if (tabButton) {
            tabButton.classList.add('active');
        }
    }

    // 激活对应的内容区域
    const contentEl = document.getElementById(tabName);
    if (contentEl) {
        contentEl.classList.add('active');
    }

    // 更新顶部标题
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
        pageTitle.textContent = `🤖 ${label}`;
    }

    // 移动端：切换后自动关闭侧边栏
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        if (sidebar) sidebar.classList.remove('mobile-open');
        if (overlay) overlay.classList.remove('active');
    }

    // 加载对应tab的数据
    if (tabName === 'sessions') loadSessions();
    if (tabName === 'memory') loadMemoryStats();
    if (tabName === 'analytics') {
        // 自动加载行为分析数据
        loadBehaviorAnalytics();
        // 自动加载主动问答历史
        const userId = 'default_user';
        loadProactiveQA(userId);
    }
    if (tabName === 'tasks') {
        // 自动加载任务列表，默认显示待完成任务
        document.getElementById('taskStatusFilter').value = 'pending';
        loadTasks();
    }
    if (tabName === 'reminders') {
        // 自动加载提醒列表
        loadReminders();
        loadReminderHistory();
    }
    if (tabName === 'documents') {
        // 自动加载文档列表
        loadDocuments();
    }
    if (tabName === 'tools') {
        // 自动加载工具列表
        loadTools();
        loadToolHistory();
    }
    if (tabName === 'schedule') {
        // 自动加载课程表
        loadSchedule();
    }
}

// ==================== v0.8.0 语音交互功能 ====================

let recognition = null;
let isRecording = false;
let speechSynthesis = window.speechSynthesis;
let currentUtterance = null;
let recognitionRetryCount = 0;
const MAX_RETRY = 2;

// v0.8.1 连续对话模式
let isConversationMode = false;
let isSpeaking = false; // AI正在说话
let currentAudio = null; // 当前播放的音频

// 监听网络状态
window.addEventListener('online', function () {
    console.log('✅ 网络已连接，语音识别可用');
});

window.addEventListener('offline', function () {
    console.warn('⚠️ 网络已断开，语音识别不可用');
    if (isRecording) {
        stopVoiceInput();
        showToast('网络断开，语音识别已停止', 'error');
    }
});

// 页面卸载时清理语音资源
window.addEventListener('beforeunload', function () {
    console.log('🧹 页面卸载，清理语音资源...');

    // 停止语音合成
    if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
    }

    // 停止音频播放
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    // 停止录音
    if (isRecording) {
        stopVoiceInput();
    }

    // 关闭对话模式
    if (isConversationMode) {
        isConversationMode = false;
    }
});

// 页面隐藏时暂停语音（切换标签页、最小化窗口等）
document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
        console.log('📵 页面隐藏，暂停语音播放');

        // 暂停语音合成
        if (speechSynthesis.speaking) {
            speechSynthesis.pause();
        }

        // 暂停音频
        if (currentAudio && !currentAudio.paused) {
            currentAudio.pause();
        }
    } else {
        console.log('📱 页面显示，恢复语音播放');

        // 恢复语音合成
        if (speechSynthesis.paused) {
            speechSynthesis.resume();
        }

        // 恢复音频（可选，避免突然播放）
        // if (currentAudio && currentAudio.paused) {
        //     currentAudio.play();
        // }
    }
});

// 初始化语音识别
function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.warn('浏览器不支持语音识别');
        return null;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();

    recognition.lang = 'zh-CN';  // 中文识别
    recognition.continuous = false;  // 不持续识别
    recognition.interimResults = true;  // 显示临时结果
    recognition.maxAlternatives = 1;  // 只返回最佳结果

    // 添加详细日志
    console.log('🔧 语音识别配置:', {
        lang: recognition.lang,
        continuous: recognition.continuous,
        interimResults: recognition.interimResults
    });

    recognition.onstart = function () {
        console.log('🎤 语音识别开始');
        isRecording = true;
        const voiceBtn = document.getElementById('voiceBtn');
        const voiceStatus = document.getElementById('voiceStatus');
        const voiceText = document.getElementById('voiceText');

        voiceBtn.classList.add('recording');
        voiceStatus.style.display = 'flex';
        voiceText.textContent = '正在聆听...';
    };

    recognition.onresult = function (event) {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }

        const voiceText = document.getElementById('voiceText');
        if (interimTranscript) {
            voiceText.textContent = interimTranscript;
        }

        if (finalTranscript) {
            console.log('✅ 识别结果:', finalTranscript);
            const input = document.getElementById('messageInput');
            input.textContent = finalTranscript;
            input.focus();

            // 连续对话模式：自动发送
            if (isConversationMode) {
                setTimeout(() => autoSendInConversationMode(finalTranscript), 500);
            }
        }
    };

    recognition.onerror = function (event) {
        console.error('❌ 语音识别错误:', event.error, event);
        const voiceText = document.getElementById('voiceText');

        switch (event.error) {
            case 'no-speech':
                voiceText.textContent = '没有检测到语音，请重试';
                break;
            case 'audio-capture':
                voiceText.textContent = '无法访问麦克风';
                break;
            case 'not-allowed':
                voiceText.textContent = '麦克风权限被拒绝';
                break;
            case 'network':
                voiceText.textContent = '网络连接失败，请检查网络后重试';
                console.warn('💡 提示: 语音识别需要网络连接，请确保网络正常');
                break;
            case 'service-not-allowed':
                voiceText.textContent = '语音服务不可用';
                break;
            case 'aborted':
                voiceText.textContent = '识别已取消';
                break;
            default:
                voiceText.textContent = `识别出错: ${event.error}`;
                console.error('未知错误类型:', event.error);
        }

        setTimeout(() => {
            stopVoiceInput();
        }, 3000);
    };

    recognition.onend = function () {
        console.log('🎤 语音识别结束');
        stopVoiceInput();
    };

    return recognition;
}

// 切换语音输入
function toggleVoiceInput() {
    // 优先使用百度语音识别
    const useBaiduVoice = localStorage.getItem('useBaiduVoice') === 'true';

    if (useBaiduVoice) {
        toggleBaiduVoiceInput();
    } else {
        toggleGoogleVoiceInput();
    }
}

// Google 语音识别（原方法）
function toggleGoogleVoiceInput() {
    // 检查网络连接
    if (!navigator.onLine) {
        alert('⚠️ 网络未连接\n\n语音识别需要网络连接，请检查您的网络设置。');
        return;
    }

    // 诊断语音识别可用性
    console.log('🔍 Google语音识别诊断:');
    console.log('- 浏览器:', navigator.userAgent);
    console.log('- 在线状态:', navigator.onLine);
    console.log('- 语音识别支持:', 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window);

    if (!recognition) {
        recognition = initSpeechRecognition();
        if (!recognition) {
            alert('❌ 浏览器不支持语音识别\n\n建议使用:\n✅ Chrome 浏览器（推荐）\n✅ Edge 浏览器\n✅ Safari 浏览器\n\n💡 提示：语音识别需要网络连接');
            return;
        }
    }

    if (isRecording) {
        recognition.stop();
    } else {
        try {
            // 显示准备提示
            const voiceStatus = document.getElementById('voiceStatus');
            const voiceText = document.getElementById('voiceText');
            voiceStatus.style.display = 'flex';
            voiceText.textContent = '正在准备...';

            recognition.start();
        } catch (e) {
            console.error('启动语音识别失败:', e);

            // 更友好的错误提示
            let errorMsg = '启动语音识别失败';
            if (e.message.includes('already started')) {
                errorMsg = '语音识别已经在运行中，请稍候';
                // 重置状态
                stopVoiceInput();
                setTimeout(() => {
                    toggleVoiceInput();
                }, 500);
                return;
            } else if (e.message.includes('not allowed')) {
                errorMsg = '麦克风权限被拒绝\n\n请在浏览器设置中允许麦克风访问';
            } else {
                errorMsg += '\n\n' + e.message;
            }

            alert('❌ ' + errorMsg + '\n\n💡 建议：刷新页面后重试');
            stopVoiceInput();
        }
    }
}

// 停止语音输入
function stopVoiceInput() {
    isRecording = false;
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceStatus = document.getElementById('voiceStatus');

    voiceBtn.classList.remove('recording');
    voiceStatus.style.display = 'none';

    // 停止百度录音器
    if (baiduRecorder && baiduRecorder.recording) {
        baiduRecorder.recording = false;

        try {
            if (baiduRecorder.processor) {
                baiduRecorder.processor.disconnect();
                baiduRecorder.processor = null;
            }
            if (baiduRecorder.source) {
                baiduRecorder.source.disconnect();
                baiduRecorder.source = null;
            }
            if (baiduRecorder.stream) {
                baiduRecorder.stream.getTracks().forEach(t => t.stop());
                baiduRecorder.stream = null;
            }
            if (baiduRecorder.audioContext) {
                baiduRecorder.audioContext.close();
                baiduRecorder.audioContext = null;
            }
            baiduRecorder.bufferL = [];
        } catch (e) {
            console.error('停止百度录音器出错:', e);
        }
    }
}

// ==================== 百度语音识别 ====================

// 基于 Web Audio API 的 WAV(PCM16) 录音器，采样率 16k 以适配百度ASR
let baiduRecorder = {
    audioContext: null,
    source: null,
    processor: null,
    analyser: null,
    stream: null,
    bufferL: [],
    sampleRate: 16000,
    recording: false,
    silenceStart: 0,
    silenceThreshold: 0.01, // 静音阈值
    silenceDuration: 1500,  // 静音持续时间（毫秒），1.5秒后自动停止
    hasSpoken: false,       // 是否检测到说话
    listeningMode: false,   // 监听模式：等待用户打断AI说话
};

function mergeBuffers(bufferArray) {
    let length = 0;
    bufferArray.forEach(b => length += b.length);
    const result = new Float32Array(length);
    let offset = 0;
    bufferArray.forEach(b => { result.set(b, offset); offset += b.length; });
    return result;
}

// 音频归一化和增益
function normalizeAndBoost(buffer, targetPeak = 0.95, minGain = 1.5) {
    // 找到最大振幅
    let max = 0;
    for (let i = 0; i < buffer.length; i++) {
        const abs = Math.abs(buffer[i]);
        if (abs > max) max = abs;
    }

    // 计算增益
    let gain = 1.0;
    if (max > 0) {
        gain = Math.max(targetPeak / max, minGain);
    } else {
        gain = minGain;
    }

    // 限制最大增益，避免过度放大噪音
    gain = Math.min(gain, 8.0);

    console.log(`🔊 音频增益: ${gain.toFixed(2)}x (原始峰值: ${(max * 100).toFixed(1)}%)`);

    // 应用增益
    const result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = Math.max(-1, Math.min(1, buffer[i] * gain));
    }

    return result;
}

function downsampleBuffer(buffer, inSampleRate, outSampleRate) {
    if (outSampleRate === inSampleRate) return buffer;
    const ratio = inSampleRate / outSampleRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
        const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
        let accum = 0, count = 0;
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        result[offsetResult] = accum / count;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

function encodeWAV(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    const bytesPerSample = 2;
    const numChannels = 1;
    const blockAlign = numChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;

    // RIFF header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * bytesPerSample, true);
    writeString(view, 8, 'WAVE');

    // fmt chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // PCM
    view.setUint16(20, 1, true);  // PCM format
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true); // 16-bit

    // data chunk
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * bytesPerSample, true);

    // PCM samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([view], { type: 'audio/wav' });
}

// 🎧 启动监听模式：在AI说话时监听用户打断
async function startListeningForInterrupt() {
    if (!isConversationMode || !isSpeaking) return;
    if (baiduRecorder.listeningMode) return; // 已经在监听中

    console.log('🎧 启动打断监听模式...');

    try {
        // 请求麦克风权限
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        // 创建音频分析器
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        const processor = audioContext.createScriptProcessor(4096, 1, 1);

        // 保存到全局对象
        baiduRecorder.listeningStream = stream;
        baiduRecorder.listeningContext = audioContext;
        baiduRecorder.listeningSource = source;
        baiduRecorder.listeningAnalyser = analyser;
        baiduRecorder.listeningProcessor = processor;
        baiduRecorder.listeningMode = true;

        // 打断检测参数
        let interruptThreshold = 0.05; // 提高阈值，避免误触发（原来0.01太低）
        let interruptCount = 0;        // 连续检测计数
        let requiredCount = 3;         // 需要连续3次检测到声音才触发（约0.3秒）
        let startDelay = 500;          // 启动后延迟500ms才开始检测，避免回声
        let startTime = Date.now();

        // 监听音频输入
        processor.onaudioprocess = function (e) {
            if (!baiduRecorder.listeningMode) return;

            // 启动延迟保护：前500ms不检测
            if (Date.now() - startTime < startDelay) {
                return;
            }

            const channel = e.inputBuffer.getChannelData(0);

            // 计算音量
            let sum = 0;
            for (let i = 0; i < channel.length; i++) {
                sum += channel[i] * channel[i];
            }
            const rms = Math.sqrt(sum / channel.length);

            // 连续性检测：需要连续多次检测到声音才触发
            if (rms > interruptThreshold) {
                interruptCount++;
                console.log(`🎤 检测到声音 (${interruptCount}/${requiredCount}): RMS=${rms.toFixed(4)}`);

                if (interruptCount >= requiredCount) {
                    console.log('✅ 确认用户说话，打断AI');

                    // 停止监听模式
                    stopListeningMode();

                    // 打断AI并开始正式录音
                    if (isSpeaking) {
                        stopSpeaking();
                    }

                    // 立即开始录音
                    setTimeout(() => {
                        if (isConversationMode && !isRecording) {
                            console.log('🎤 从监听模式切换到录音模式');
                            toggleBaiduVoiceInput();
                        }
                    }, 100);
                }
            } else {
                // 没有声音，重置计数
                if (interruptCount > 0) {
                    console.log(`🔇 声音中断，重置计数 (之前: ${interruptCount})`);
                }
                interruptCount = 0;
            }
        };

        // 连接音频节点
        source.connect(analyser);
        analyser.connect(processor);
        processor.connect(audioContext.destination);

        console.log('✅ 打断监听模式已激活');

    } catch (error) {
        console.error('❌ 启动监听模式失败:', error);
        baiduRecorder.listeningMode = false;
    }
}

// 停止监听模式
function stopListeningMode() {
    if (!baiduRecorder.listeningMode) return;

    console.log('🛑 停止打断监听模式');

    try {
        if (baiduRecorder.listeningProcessor) {
            baiduRecorder.listeningProcessor.disconnect();
            baiduRecorder.listeningProcessor = null;
        }
        if (baiduRecorder.listeningAnalyser) {
            baiduRecorder.listeningAnalyser.disconnect();
            baiduRecorder.listeningAnalyser = null;
        }
        if (baiduRecorder.listeningSource) {
            baiduRecorder.listeningSource.disconnect();
            baiduRecorder.listeningSource = null;
        }
        if (baiduRecorder.listeningStream) {
            baiduRecorder.listeningStream.getTracks().forEach(track => track.stop());
            baiduRecorder.listeningStream = null;
        }
        if (baiduRecorder.listeningContext) {
            baiduRecorder.listeningContext.close();
            baiduRecorder.listeningContext = null;
        }
    } catch (e) {
        console.log('清理监听模式资源:', e);
    }

    baiduRecorder.listeningMode = false;
}

async function toggleBaiduVoiceInput() {
    if (isRecording) {
        // 手动停止录音并识别
        await processBaiduRecording();
        return;
    }

    // 如果AI正在说话，先停止
    if (isSpeaking) {
        console.log('⏸️ 打断AI说话，开始录音');
        stopSpeaking();
    }

    try {
        // 先清理之前的录音器状态
        if (baiduRecorder.audioContext) {
            try {
                await baiduRecorder.audioContext.close();
            } catch (e) {
                console.log('关闭旧AudioContext:', e);
            }
        }

        // 重置录音器对象
        baiduRecorder = {
            audioContext: null,
            source: null,
            processor: null,
            analyser: null,
            stream: null,
            bufferL: [],
            sampleRate: 16000,
            recording: false,
            silenceStart: 0,
            silenceThreshold: 0.01,
            silenceDuration: 1500,
            hasSpoken: false,
        };

        // 请求麦克风权限
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        // 显示录音状态
        isRecording = true;
        const voiceBtn = document.getElementById('voiceBtn');
        const voiceStatus = document.getElementById('voiceStatus');
        const voiceText = document.getElementById('voiceText');

        voiceBtn.classList.add('recording');
        voiceStatus.style.display = 'flex';
        voiceText.textContent = '请开始说话...';

        // 创建 Web Audio 录音流程
        baiduRecorder.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        baiduRecorder.stream = stream;
        baiduRecorder.source = baiduRecorder.audioContext.createMediaStreamSource(stream);
        baiduRecorder.analyser = baiduRecorder.audioContext.createAnalyser();
        baiduRecorder.analyser.fftSize = 2048;
        baiduRecorder.processor = baiduRecorder.audioContext.createScriptProcessor(4096, 1, 1);
        baiduRecorder.bufferL = [];
        baiduRecorder.recording = true;
        baiduRecorder.silenceStart = Date.now();

        // 音频处理和静音检测
        baiduRecorder.processor.onaudioprocess = function (e) {
            if (!baiduRecorder.recording) return;

            const channel = e.inputBuffer.getChannelData(0);
            // 拷贝数据
            baiduRecorder.bufferL.push(new Float32Array(channel));

            // 计算音量（RMS）
            let sum = 0;
            for (let i = 0; i < channel.length; i++) {
                sum += channel[i] * channel[i];
            }
            const rms = Math.sqrt(sum / channel.length);

            // 静音检测
            if (rms > baiduRecorder.silenceThreshold) {
                // 检测到声音
                if (!baiduRecorder.hasSpoken) {
                    // 第一次检测到声音
                    baiduRecorder.hasSpoken = true;

                    // 🎯 连续对话模式：检测到用户说话，立即打断AI
                    if (isConversationMode && isSpeaking) {
                        console.log('👂 检测到用户说话，打断AI播放');
                        stopSpeaking();
                        const stateText = document.getElementById('conversationStateText');
                        if (stateText) {
                            stateText.textContent = '正在录音...';
                        }
                    }
                }

                baiduRecorder.silenceStart = Date.now();
                voiceText.textContent = '正在录音...🎤';
            } else if (baiduRecorder.hasSpoken) {
                // 说话后的静音
                const silenceDuration = Date.now() - baiduRecorder.silenceStart;
                if (silenceDuration > baiduRecorder.silenceDuration) {
                    console.log('🔇 检测到静音，自动停止录音');
                    voiceText.textContent = '检测到静音，正在识别...';
                    // 自动停止并识别
                    setTimeout(() => processBaiduRecording(), 100);
                }
            }
        };

        // 连接音频节点
        baiduRecorder.source.connect(baiduRecorder.analyser);
        baiduRecorder.analyser.connect(baiduRecorder.processor);
        baiduRecorder.processor.connect(baiduRecorder.audioContext.destination);

        console.log('🎤 百度语音录音开始 (自动静音检测)');
        console.log('   AudioContext采样率:', baiduRecorder.audioContext.sampleRate);
        console.log('   静音阈值:', baiduRecorder.silenceThreshold);
        console.log('   静音时长:', baiduRecorder.silenceDuration + 'ms');

    } catch (error) {
        console.error('❌ 麦克风访问失败:', error);

        let errorMsg = '无法访问麦克风';
        if (error.name === 'NotAllowedError') {
            errorMsg = '麦克风权限被拒绝\n\n请在浏览器设置中允许麦克风访问';
        } else if (error.name === 'NotFoundError') {
            errorMsg = '未找到麦克风设备\n\n请检查麦克风是否正常连接';
        } else if (error.name === 'NotReadableError') {
            errorMsg = '麦克风被其他程序占用\n\n请关闭其他使用麦克风的程序';
        }

        showToast('❌ ' + errorMsg, 'error');
        stopVoiceInput();
    }
}

// 处理百度录音识别
async function processBaiduRecording() {
    if (!baiduRecorder || !baiduRecorder.recording) return;

    try {
        baiduRecorder.recording = false;

        if (baiduRecorder.processor) {
            baiduRecorder.processor.disconnect();
        }
        if (baiduRecorder.analyser) {
            baiduRecorder.analyser.disconnect();
        }
        if (baiduRecorder.source) {
            baiduRecorder.source.disconnect();
        }
        if (baiduRecorder.stream) {
            baiduRecorder.stream.getTracks().forEach(t => t.stop());
        }

        // 检查是否录到音频
        if (baiduRecorder.bufferL.length === 0) {
            showToast('⚠️ 未检测到音频输入', 'warning');
            stopVoiceInput();
            return;
        }

        // 合并、增益、降采样并编码为 WAV 16k
        const raw = mergeBuffers(baiduRecorder.bufferL);
        const boosted = normalizeAndBoost(raw);
        const inRate = baiduRecorder.audioContext.sampleRate;
        const down = downsampleBuffer(boosted, inRate, 16000);
        const wavBlob = encodeWAV(down, 16000);

        // 上传识别
        const voiceText = document.getElementById('voiceText');
        voiceText.textContent = '正在识别...';

        const formData = new FormData();
        formData.append('file', wavBlob, 'audio.wav');
        const response = await fetch('/api/voice/recognize', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (result.success) {
            const input = document.getElementById('messageInput');
            input.textContent = result.text;
            input.focus();
            showToast('✅ 识别成功', 'success');

            // 连续对话模式：自动发送
            if (isConversationMode) {
                setTimeout(() => autoSendInConversationMode(result.text), 500);
            }
        } else {
            showToast('❌ 识别失败: ' + (result.error || '未知错误'), 'error');
        }
    } catch (e) {
        console.error('停止或识别出错:', e);
        showToast('❌ 识别请求失败', 'error');
    } finally {
        stopVoiceInput();
    }
}

// ==================== v0.8.1 连续对话模式 ====================

// 切换连续对话模式
function toggleConversationMode() {
    isConversationMode = !isConversationMode;

    const btn = document.getElementById('conversationModeBtn');
    const statusDiv = document.getElementById('conversationModeStatus');
    const stateText = document.getElementById('conversationStateText');

    if (isConversationMode) {
        // 开启对话模式
        btn.classList.add('active');
        statusDiv.style.display = 'block';
        stateText.textContent = '对话模式已开启';
        showToast('🎤 连续对话模式已开启', 'success');
        console.log('🔊 连续对话模式：已开启');

        // 自动开始第一轮录音
        setTimeout(() => {
            if (isConversationMode && !isRecording && !isSpeaking) {
                startConversationRound();
            }
        }, 500);
    } else {
        // 关闭对话模式
        btn.classList.remove('active');
        statusDiv.style.display = 'none';
        showToast('⏸️ 连续对话模式已关闭', 'info');
        console.log('🔇 连续对话模式：已关闭');

        // 停止当前录音
        if (isRecording) {
            stopVoiceInput();
        }
        // 停止当前播放
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        if (currentUtterance) {
            speechSynthesis.cancel();
            currentUtterance = null;
        }
        isSpeaking = false;
    }
}

// 开始一轮对话（录音）
function startConversationRound() {
    if (!isConversationMode) return;
    if (isRecording) return; // 只检查录音状态，允许打断AI说话

    // 如果AI正在说话，先停止
    if (isSpeaking) {
        console.log('⏸️ 打断AI说话，开始新录音');
        stopSpeaking();
    }

    console.log('🎤 开始新一轮对话录音...');
    const stateText = document.getElementById('conversationStateText');
    stateText.textContent = '请开始说话...';

    // 触发语音输入
    toggleVoiceInput();
}

// 在识别成功后自动发送（连续对话模式专用）
async function autoSendInConversationMode(text) {
    if (!isConversationMode) return;

    console.log('📤 连续对话模式：自动发送消息');
    const stateText = document.getElementById('conversationStateText');
    stateText.textContent = 'AI正在思考...';

    // 填入输入框
    const input = document.getElementById('messageInput');
    input.textContent = text;

    // 自动发送
    await sendMessageFromDiv();
}

// 在AI回复播放完成后继续下一轮
function onSpeechEnd() {
    isSpeaking = false;
    console.log('🔚 语音播放完成');

    // 停止监听模式
    stopListeningMode();

    if (isConversationMode) {
        console.log('♻️ 连续对话模式：准备下一轮');
        const stateText = document.getElementById('conversationStateText');
        stateText.textContent = '请继续说话...';

        // 等待1秒后开始下一轮
        setTimeout(() => {
            if (isConversationMode && !isRecording && !isSpeaking) {
                startConversationRound();
            }
        }, 1000);
    }
}

// 语音播放AI回复（支持 WebSpeech 或 百度TTS）
async function speakText(text, forcePlay = false) {
    // 检查是否启用自动播放（连续对话模式强制播放）
    const autoPlay = localStorage.getItem('voiceAutoPlay') === 'true' || isConversationMode || forcePlay;
    if (!autoPlay) return;

    isSpeaking = true;

    // 显示全局停止按钮
    const globalStopBtn = document.getElementById('globalStopSpeakingBtn');
    if (globalStopBtn) {
        globalStopBtn.style.display = 'flex';
    }

    // 显示播放状态指示器
    const speakingStatus = document.getElementById('speakingStatus');
    if (speakingStatus) {
        speakingStatus.style.display = 'flex';
    }

    if (isConversationMode) {
        const stateText = document.getElementById('conversationStateText');
        stateText.textContent = 'AI正在回复...（点击🎤或按空格打断）';

        // 不再自动启动监听模式，改为用户主动打断
        // startListeningForInterrupt();
    }

    const ttsProvider = (localStorage.getItem('ttsProvider') || 'web').toLowerCase();
    if (ttsProvider === 'baidu') {
        try {
            const resp = await fetch('/api/voice/synthesize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text,
                    person: parseInt(localStorage.getItem('ttsPerson') || '0', 10),
                    speed: parseInt(localStorage.getItem('voiceRateNum') || '5', 10),
                    pitch: 5,
                    volume: Math.round(parseFloat(localStorage.getItem('voiceVolume') || '1.0') * 10),
                    audio_format: 'mp3'
                })
            });
            const data = await resp.json();
            if (data.success) {
                currentAudio = new Audio(`data:${data.mime};base64,${data.audio_base64}`);
                currentAudio.onended = () => {
                    currentAudio = null;
                    // 隐藏停止按钮和播放状态
                    if (globalStopBtn) {
                        globalStopBtn.style.display = 'none';
                    }
                    const speakingStatus = document.getElementById('speakingStatus');
                    if (speakingStatus) {
                        speakingStatus.style.display = 'none';
                    }
                    onSpeechEnd();
                };
                currentAudio.onerror = () => {
                    currentAudio = null;
                    isSpeaking = false;
                    // 隐藏停止按钮和播放状态
                    if (globalStopBtn) {
                        globalStopBtn.style.display = 'none';
                    }
                    const speakingStatus = document.getElementById('speakingStatus');
                    if (speakingStatus) {
                        speakingStatus.style.display = 'none';
                    }
                };
                currentAudio.play().catch(e => {
                    console.warn('自动播放受阻:', e);
                    isSpeaking = false;
                    // 隐藏停止按钮和播放状态
                    if (globalStopBtn) {
                        globalStopBtn.style.display = 'none';
                    }
                    const speakingStatus = document.getElementById('speakingStatus');
                    if (speakingStatus) {
                        speakingStatus.style.display = 'none';
                    }
                });
                return;
            } else {
                console.warn('百度TTS失败，回退到WebSpeech:', data.error);
            }
        } catch (e) {
            console.warn('百度TTS调用异常，回退到WebSpeech:', e);
        }
    }

    // 停止当前播放
    if (currentUtterance) {
        speechSynthesis.cancel();
    }

    // 创建新的语音合成实例
    currentUtterance = new SpeechSynthesisUtterance(text);
    currentUtterance.lang = 'zh-CN';
    currentUtterance.rate = parseFloat(localStorage.getItem('voiceRate') || '1.0');
    currentUtterance.volume = parseFloat(localStorage.getItem('voiceVolume') || '1.0');

    currentUtterance.onstart = function () {
        console.log('🔊 开始播放语音');
    };

    currentUtterance.onend = function () {
        console.log('🔊 播放结束');
        currentUtterance = null;
        // 隐藏停止按钮和播放状态
        if (globalStopBtn) {
            globalStopBtn.style.display = 'none';
        }
        const speakingStatus = document.getElementById('speakingStatus');
        if (speakingStatus) {
            speakingStatus.style.display = 'none';
        }
        onSpeechEnd();
    };

    currentUtterance.onerror = function (event) {
        console.error('语音播放错误:', event.error);
        currentUtterance = null;
        isSpeaking = false;
        // 隐藏停止按钮和播放状态
        if (globalStopBtn) {
            globalStopBtn.style.display = 'none';
        }
        const speakingStatus = document.getElementById('speakingStatus');
        if (speakingStatus) {
            speakingStatus.style.display = 'none';
        }
    };

    speechSynthesis.speak(currentUtterance);
}

// 停止语音播放
// 停止语音播放
function stopSpeaking() {
    console.log('🛑 停止所有语音播放');

    // 停止 Web Speech API
    if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
        currentUtterance = null;
    }

    // 停止百度TTS音频
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0; // 重置播放位置
        currentAudio = null;
    }

    // 停止监听模式
    stopListeningMode();

    // 重置说话状态
    isSpeaking = false;

    // 隐藏全局停止按钮和播放状态
    const globalStopBtn = document.getElementById('globalStopSpeakingBtn');
    if (globalStopBtn) {
        globalStopBtn.style.display = 'none';
    }

    const speakingStatus = document.getElementById('speakingStatus');
    if (speakingStatus) {
        speakingStatus.style.display = 'none';
    }

    showToast('⏸️ 语音播放已停止', 'info');
}

// ==================== 发送消息功能 ====================

// 发送消息（从contenteditable div）
async function sendMessageFromDiv() {
    const input = document.getElementById('messageInput');
    const message = input.textContent.trim();

    // 如果既没有文字也没有图片，直接返回
    if (!message && !uploadedImagePath) return;

    // 如果有图片但没有文字，使用默认提示词
    const actualMessage = message || '请详细描述这张图片的内容';

    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    input.contentEditable = 'false';

    // 检查是否处于编辑模式 v0.6.0
    if (editingMessage) {
        // 删除原来的消息及其后续的AI回复
        const messageId = editingMessage.dataset.messageId;

        // 调用后端 API 删除该消息及之后的所有消息
        if (messageId) {
            try {
                const response = await fetch(`/messages/${messageId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });
                if (!response.ok) {
                    console.warn('删除消息失败，继续前端删除');
                }
            } catch (e) {
                console.warn('删除消息请求失败:', e);
            }
        }

        // 找到该消息后的所有消息并删除 DOM
        let nextElement = editingMessage.nextElementSibling;
        while (nextElement && nextElement.classList.contains('message')) {
            const toRemove = nextElement;
            nextElement = nextElement.nextElementSibling;
            toRemove.remove();
        }

        // 删除原用户消息
        editingMessage.remove();

        // 清除编辑状态
        clearEditingState();

        // 继续正常发送流程，触发新的回复
        // 不要 return，让代码继续执行下面的发送逻辑
    }

    // 显示用户消息（包含图片）
    let displayMessage = message || '识别图片';
    addMessage('user', displayMessage, null, uploadedImagePath);
    input.textContent = '';

    // 保存当前图片路径（用于API调用）
    const currentImagePath = uploadedImagePath;

    // 立即清除图片预览和上传状态
    removeImagePreview();

    try {
        // 获取设置
        const settings = getSettings();
        const responseStyle = settings.responseStyle || 'balanced';

        // 检测是否包含"记住"等关键词
        const memorizeKeywords = ['记住', '保存', '记下', '存一下', '记录'];
        const shouldMemorize = message && memorizeKeywords.some(kw => message.includes(kw));

        // 构建请求 URL（添加图片路径和记忆标志）
        let url = `${API_BASE}/chat?prompt=${encodeURIComponent(message || '')}&response_style=${responseStyle}`;

        if (currentSessionId) {
            url += `&session_id=${currentSessionId}`;
        }

        if (currentImagePath) {
            url += `&image_path=${encodeURIComponent(currentImagePath)}`;
        }

        if (shouldMemorize) {
            url += `&memorize=true`;
            console.log('🧠 检测到记忆关键词，将保存图片内容到记忆库');
        }

        console.log('📤 发送请求:', url);

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

            // v0.7.1: 已禁用追问弹窗，小乐通过正常对话主动提问
            // if (data.followup) {
            //     showFollowupSuggestion(data.followup);
            // }
        } else {
            addMessage('assistant', '抱歉，出现错误：' + (data.detail || '未知错误'));
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            addMessage('assistant', '请求超时，问题可能比较复杂，请稍后再试。');
        } else {
            addMessage('assistant', '网络错误：' + error.message);
        }
    } finally {
        sendBtn.disabled = false;
        input.contentEditable = 'true';
        input.focus();
    }
}

// 发送消息（保留旧函数兼容性）
async function sendMessage() {
    const input = document.getElementById('messageInput');
    // 检查是否是contenteditable
    if (input.contentEditable === 'true') {
        sendMessageFromDiv();
        return;
    }

    const message = input.value.trim();

    // 如果有图片但没有文字，提示用户
    if (!message && uploadedImagePath) {
        showNotification('请输入对图片的提问', 'warning');
        return;
    }

    if (!message && !uploadedImagePath) return;

    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    input.disabled = true;

    // 显示用户消息
    let displayMessage = message;
    if (uploadedImagePath) {
        displayMessage = `📷 [图片]\n${message}`;
    }
    addMessage('user', displayMessage);
    input.value = '';
    // 重置textarea高度
    input.style.height = 'auto';

    try {
        // 如果有上传的图片，先调用图片识别API并将分析结果作为上下文发送到聊天接口
        if (uploadedImagePath) {
            console.log('🖼️ 发送图片识别请求:', uploadedImagePath);
            const response = await fetch('/api/vision/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image_path: uploadedImagePath,
                    prompt: message || '请详细描述这张图片的内容'
                })
            });

            const result = await response.json();

            if (result.success) {
                // 在聊天中显示图片的分析（作为可见的上下文）
                addMessage('assistant', `📷 图片分析：${result.description}\n\n_${result.model}_`);

                // 将用户的文本和图片分析合并，发送到聊天接口，让小乐基于图片与问题作答
                const settings = getSettings();
                const responseStyle = settings.responseStyle || 'balanced';

                const combinedPrompt = message
                    ? `${message}\n\n根据上面的图片分析，回答用户的问题。图片分析摘要：${result.description}`
                    : `请基于图片内容给出详细描述：${result.description}`;

                const url = currentSessionId
                    ? `${API_BASE}/chat?prompt=${encodeURIComponent(combinedPrompt)}&session_id=${currentSessionId}&response_style=${responseStyle}`
                    : `${API_BASE}/chat?prompt=${encodeURIComponent(combinedPrompt)}&response_style=${responseStyle}`;

                // 设置60秒超时
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 60000);

                const chatResp = await fetch(url, {
                    method: 'POST',
                    signal: controller.signal
                });
                clearTimeout(timeoutId);

                const chatData = await chatResp.json();

                if (chatResp.ok) {
                    currentSessionId = chatData.session_id;
                    addMessage('assistant', chatData.reply);
                } else {
                    addMessage('assistant', '抱歉，图片相关的问题处理失败：' + (chatData.detail || chatData.error || '未知错误'));
                }

                // 清理图片预览（保留，如需历史可改为保留）
                removeImagePreview();
            } else {
                addMessage('assistant', `❌ 图片识别失败: ${result.error}`);
            }
        } else {
            // 普通文本消息
            // v0.6.0: 获取用户设置的响应风格
            const settings = getSettings();
            const responseStyle = settings.responseStyle || 'balanced';

            const url = currentSessionId
                ? `${API_BASE}/chat?prompt=${encodeURIComponent(message)}&session_id=${currentSessionId}&response_style=${responseStyle}`
                : `${API_BASE}/chat?prompt=${encodeURIComponent(message)}&response_style=${responseStyle}`;

            // 设置60秒超时以处理复杂问题
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
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            addMessage('assistant', '请求超时，问题可能比较复杂，请稍后再试。');
        } else {
            addMessage('assistant', '网络错误：' + error.message);
        }
    } finally {
        sendBtn.disabled = false;
        input.disabled = false;
        input.focus();
    }
}

// 添加消息到界面
function addMessage(role, content, messageId = null, imagePath = null, shouldPlayVoice = true) {
    const container = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    // 设置消息ID用于编辑/删除
    if (messageId) {
        messageDiv.dataset.messageId = messageId;
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // 如果有图片，先显示图片
    if (imagePath && role === 'user') {
        const imageDiv = document.createElement('div');
        imageDiv.className = 'message-image';
        const img = document.createElement('img');
        img.src = `/${imagePath}`;
        img.alt = '上传的图片';
        img.style.cssText = 'max-width: 300px; max-height: 300px; border-radius: 8px; margin-bottom: 8px;';
        img.onclick = () => openImageViewer(`/${imagePath}`);
        imageDiv.appendChild(img);
        contentDiv.appendChild(imageDiv);

        // 清理消息内容：移除视觉识别结果的XML标签
        // 只保留用户问题部分
        const userQuestionMatch = content.match(/用户问题：(.+?)(?=\n\n请基于|$)/s);
        if (userQuestionMatch) {
            content = userQuestionMatch[1].trim();
        } else {
            // 兼容旧格式：移除 [图片内容]: 和 [用户问题]: 标记
            const oldFormatMatch = content.match(/\[用户问题\]:\s*(.+)/s);
            if (oldFormatMatch) {
                content = oldFormatMatch[1].trim();
            } else {
                // 移除 <vision_result> 标签内容
                content = content.replace(/<vision_result>[\s\S]*?<\/vision_result>/g, '').trim();
                // 移除"请基于..."等系统提示
                content = content.replace(/\n\n请基于.*?问题。?$/s, '').trim();
            }
        }
    }

    // 添加文本内容
    const textDiv = document.createElement('div');
    // 如果是助手消息，使用Markdown渲染；用户消息保持纯文本
    if (role === 'assistant') {
        textDiv.innerHTML = marked.parse(content);

        // v0.8.0 语音播放AI回复（检查自动播放设置）
        const autoPlayEnabled = localStorage.getItem('voiceAutoPlay') === 'true';
        if (shouldPlayVoice && autoPlayEnabled) {
            setTimeout(() => {
                speakText(content);
            }, 100);
        }

        // 为AI消息添加操作按钮
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions ai-actions';

        // 复制按钮
        const copyBtn = document.createElement('button');
        copyBtn.className = 'message-action-btn copy';
        copyBtn.innerHTML = '📋';
        copyBtn.title = '复制内容';
        copyBtn.onclick = () => copyMessage(content, copyBtn);

        // 朗读按钮
        const speakBtn = document.createElement('button');
        speakBtn.className = 'message-action-btn speak';
        speakBtn.innerHTML = '🔊';
        speakBtn.title = '朗读内容';
        speakBtn.onclick = () => speakText(content, true);  // 强制播放

        // 最佳回复按钮
        const goodBtn = document.createElement('button');
        goodBtn.className = 'message-action-btn good';
        goodBtn.innerHTML = '⭐';
        goodBtn.title = '标记为最佳回复';
        goodBtn.onclick = () => markAsGoodResponse(messageDiv, content);

        // 错误回复按钮
        const badBtn = document.createElement('button');
        badBtn.className = 'message-action-btn bad';
        badBtn.innerHTML = '❌';
        badBtn.title = '标记为错误回复';
        badBtn.onclick = () => markAsBadResponse(messageDiv, content);

        actionsDiv.appendChild(copyBtn);
        actionsDiv.appendChild(speakBtn);
        actionsDiv.appendChild(goodBtn);
        actionsDiv.appendChild(badBtn);

        // 先添加文本，再添加按钮
        contentDiv.appendChild(textDiv);
        contentDiv.appendChild(actionsDiv);
    } else {
        textDiv.textContent = content;

        // 为用户消息添加操作按钮
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';

        // 复制按钮
        const copyBtn = document.createElement('button');
        copyBtn.className = 'message-action-btn copy';
        copyBtn.innerHTML = '📋';
        copyBtn.title = '复制消息';
        copyBtn.onclick = () => copyMessage(content, copyBtn);

        // 编辑按钮
        const editBtn = document.createElement('button');
        editBtn.className = 'message-action-btn edit';
        editBtn.innerHTML = '✏️';
        editBtn.title = '编辑消息';
        editBtn.onclick = () => editMessage(messageDiv, content, imagePath);

        actionsDiv.appendChild(copyBtn);
        actionsDiv.appendChild(editBtn);

        // 先添加文本，再添加按钮
        contentDiv.appendChild(textDiv);
        contentDiv.appendChild(actionsDiv);
    }

    messageDiv.appendChild(contentDiv);
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

// 新对话
function newChat() {
    currentSessionId = null;
    document.getElementById('chatContainer').innerHTML = '';
    document.getElementById('sessionInfo').style.display = 'none';
    document.getElementById('messageInput').focus();

    // 清除编辑状态
    clearEditingState();
}

// ============ v0.6.0 消息操作功能 ============

let editingMessage = null;
let originalContent = '';
let editingImagePath = null;

// 编辑消息
function editMessage(messageDiv, content, imagePath = null) {
    const input = document.getElementById('messageInput');

    // 保存编辑状态
    editingMessage = messageDiv;
    originalContent = input.textContent;
    editingImagePath = imagePath;

    // 将消息内容加载到输入框
    input.textContent = content;
    input.focus();

    // 如果有图片，显示图片预览
    if (imagePath) {
        showImagePreviewInInput(imagePath);
    }

    // 显示编辑提示
    showEditingIndicator();
}

// 显示编辑状态提示
function showEditingIndicator() {
    // 移除已存在的提示
    const existing = document.querySelector('.editing-indicator');
    if (existing) existing.remove();

    const indicator = document.createElement('div');
    indicator.className = 'editing-indicator';
    indicator.innerHTML = `
                <span>✏️ 正在编辑消息</span>
                <button onclick="clearEditingState()">取消</button>
            `;
    document.body.appendChild(indicator);
}

// 清除编辑状态
function clearEditingState() {
    editingMessage = null;
    editingImagePath = null;
    originalContent = '';

    const indicator = document.querySelector('.editing-indicator');
    if (indicator) indicator.remove();
}

// 删除消息
function deleteMessage(messageDiv) {
    if (confirm('确定要删除这条消息吗？')) {
        // 找到对应的AI回复并一起删除
        let nextElement = messageDiv.nextElementSibling;
        if (nextElement && nextElement.classList.contains('message') &&
            (nextElement.classList.contains('ai') || nextElement.classList.contains('assistant'))) {
            nextElement.remove();
        }

        // 删除用户消息
        messageDiv.remove();

        // 显示删除成功提示
        showToast('消息已删除', 'success');
    }
}

// 复制消息
async function copyMessage(content, button) {
    try {
        // 如果content包含HTML标签，提取纯文本
        let textToCopy = content;

        // 创建临时div来解析HTML并提取纯文本
        if (content.includes('<') || content.includes('>')) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content;

            // 处理代码块：直接提取文本，不修改DOM
            const codeBlocks = tempDiv.querySelectorAll('pre code');
            let processedText = tempDiv.innerHTML;
            codeBlocks.forEach(code => {
                const codeText = code.textContent;
                const pre = code.closest('pre');
                if (pre) {
                    const placeholder = `___CODE_BLOCK___${codeText}___END_CODE___`;
                    processedText = processedText.replace(pre.outerHTML, placeholder);
                }
            });

            // 重新设置HTML
            tempDiv.innerHTML = processedText;

            // 获取纯文本
            textToCopy = tempDiv.textContent
                .replace(/___CODE_BLOCK___/g, '\n```\n')
                .replace(/___END_CODE___/g, '\n```\n')
                .replace(/\n{3,}/g, '\n\n')  // 移除多余空行
                .trim();
        }

        await navigator.clipboard.writeText(textToCopy);

        // 临时改变按钮显示
        const originalText = button.innerHTML;
        button.innerHTML = '✓';
        button.style.background = '#4CAF50';
        button.style.color = 'white';

        setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = '';
            button.style.color = '';
        }, 1000);

        showToast('已复制到剪贴板', 'success');
    } catch (err) {
        console.error('复制失败:', err);
        showToast('复制失败', 'error');
    }
}

// 标记为最佳回复
async function markAsGoodResponse(messageDiv, content) {
    console.log('🎯 markAsGoodResponse 被调用', { messageDiv, content: content.substring(0, 50) });

    try {
        // 视觉反馈：添加标记
        const contentDiv = messageDiv.querySelector('.message-content');
        if (!contentDiv) {
            console.error('❌ 找不到 .message-content');
            return;
        }

        const existingMark = contentDiv.querySelector('.feedback-mark');
        if (existingMark) {
            existingMark.remove();
        }

        const markDiv = document.createElement('div');
        markDiv.className = 'feedback-mark good';
        markDiv.innerHTML = '⭐ 最佳回复';
        markDiv.style.cssText = `
                    display: inline-block;
                    padding: 2px 8px;
                    background: linear-gradient(135deg, #fbbf24, #f59e0b);
                    color: white;
                    border-radius: 10px;
                    font-size: 11px;
                    font-weight: 500;
                    margin-left: 8px;
                    box-shadow: 0 2px 6px rgba(251, 191, 36, 0.3);
                    animation: fadeInDown 0.3s;
                `;

        // 添加到操作按钮区域前
        const actionsDiv = contentDiv.querySelector('.message-actions');
        if (actionsDiv) {
            contentDiv.insertBefore(markDiv, actionsDiv);
            console.log('✅ 标记已添加');
        }

        console.log('📡 发送反馈到服务器...', { session_id: currentSessionId });

        // 调用后端API存储反馈
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                message_content: content,
                feedback_type: 'good',
                timestamp: new Date().toISOString()
            })
        });

        console.log('📡 服务器响应:', response.status);

        if (!response.ok) {
            const errorData = await response.json();
            console.error('❌ 服务器错误:', errorData);
            throw new Error('反馈提交失败: ' + (errorData.detail || response.statusText));
        }

        const result = await response.json();
        console.log('✅ 反馈成功:', result);

        showToast('✅ 感谢反馈！这将帮助小乐变得更好', 'success');
    } catch (err) {
        console.error('❌ 标记失败:', err);
        showToast('标记失败: ' + err.message, 'error');
    }
}

// 标记为错误回复
async function markAsBadResponse(messageDiv, content) {
    console.log('🎯 markAsBadResponse 被调用', { messageDiv, content: content.substring(0, 50) });

    try {
        // 视觉反馈：添加标记
        const contentDiv = messageDiv.querySelector('.message-content');
        if (!contentDiv) {
            console.error('❌ 找不到 .message-content');
            return;
        }

        const existingMark = contentDiv.querySelector('.feedback-mark');
        if (existingMark) {
            existingMark.remove();
        }

        const markDiv = document.createElement('div');
        markDiv.className = 'feedback-mark bad';
        markDiv.innerHTML = '❌ 需要改进';
        markDiv.style.cssText = `
                    display: inline-block;
                    padding: 2px 8px;
                    background: linear-gradient(135deg, #ef4444, #dc2626);
                    color: white;
                    border-radius: 10px;
                    font-size: 11px;
                    font-weight: 500;
                    margin-left: 8px;
                    box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);
                    animation: fadeInDown 0.3s;
                `;

        // 添加到操作按钮区域前
        const actionsDiv = contentDiv.querySelector('.message-actions');
        if (actionsDiv) {
            contentDiv.insertBefore(markDiv, actionsDiv);
            console.log('✅ 标记已添加');
        }

        console.log('📡 发送反馈到服务器...', { session_id: currentSessionId });

        // 调用后端API存储反馈
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                message_content: content,
                feedback_type: 'bad',
                timestamp: new Date().toISOString()
            })
        });

        console.log('📡 服务器响应:', response.status);

        if (!response.ok) {
            const errorData = await response.json();
            console.error('❌ 服务器错误:', errorData);
            throw new Error('反馈提交失败: ' + (errorData.detail || response.statusText));
        }

        const result = await response.json();
        console.log('✅ 反馈成功:', result);

        showToast('✅ 感谢反馈！小乐会努力改进', 'success');
    } catch (err) {
        console.error('❌ 标记失败:', err);
        showToast('标记失败: ' + err.message, 'error');
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 24px;
                background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#ff6b6b' : '#667eea'};
                color: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                z-index: 10000;
                animation: slideInRight 0.3s;
                font-size: 14px;
            `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// ============ 消息操作功能结束 ============


// 加载会话列表
async function loadSessions() {
    const container = document.getElementById('sessionsList');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const response = await fetch(`${API_BASE}/sessions?all_sessions=true`);
        const data = await response.json();

        if (data.sessions && data.sessions.length > 0) {
            container.innerHTML = data.sessions.map(session => `
                        <div class="session-item ${session.session_id === currentSessionId ? 'active' : ''}"
                             data-session-id="${session.session_id}"
                             style="cursor: pointer;">
                            <div class="session-title">${session.title}</div>
                            <div class="session-time">
                                创建: ${session.created_at} | 更新: ${session.updated_at}
                            </div>
                            <!-- session-actions 导出按钮已移除 -->
                        </div>
                    `).join('');

            // 为每个会话项添加事件监听器（更安全的方式）
            container.querySelectorAll('.session-item').forEach(item => {
                item.addEventListener('click', function (e) {
                    e.preventDefault();
                    const sessionId = this.getAttribute('data-session-id');
                    if (sessionId) {
                        loadSession(sessionId);
                    }
                });
            });
        } else {
            container.innerHTML = '<div class="loading">还没有会话记录</div>';
        }
    } catch (error) {
        console.error('加载会话失败:', error);
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

// ===== 会话导出功能 =====

/**
 * 导出会话为指定格式
 * @param {string} sessionId - 会话ID
 * @param {string} format - 导出格式 ('markdown' 或 'json')
 */
async function exportSession(sessionId, format) {
    try {
        console.log(`导出会话 ${sessionId} 为 ${format} 格式`);

        // 获取会话数据
        const response = await fetch(`${API_BASE}/session/${sessionId}`);
        if (!response.ok) {
            throw new Error(`获取会话失败: ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        const messages = data.messages || [];
        const title = data.title || '未命名会话';
        const createdAt = data.created_at || new Date().toISOString();

        let content, filename, mimeType;

        if (format === 'markdown') {
            // 生成Markdown格式
            content = generateMarkdown(title, createdAt, messages);
            filename = `${sanitizeFilename(title)}_${getTimestamp()}.md`;
            mimeType = 'text/markdown';
        } else if (format === 'json') {
            // 生成JSON格式
            content = JSON.stringify({
                session_id: sessionId,
                title: title,
                created_at: createdAt,
                exported_at: new Date().toISOString(),
                message_count: messages.length,
                messages: messages.map(msg => ({
                    role: msg.role,
                    content: msg.content,
                    timestamp: msg.timestamp || msg.created_at
                }))
            }, null, 2);
            filename = `${sanitizeFilename(title)}_${getTimestamp()}.json`;
            mimeType = 'application/json';
        } else {
            throw new Error('不支持的导出格式');
        }

        // 下载文件
        downloadFile(content, filename, mimeType);
        showToast(`✅ 导出成功: ${filename}`, 'success');

    } catch (error) {
        console.error('导出失败:', error);
        showToast(`❌ 导出失败: ${error.message}`, 'error');
    }
}

/**
 * 生成Markdown格式的会话内容
 */
function generateMarkdown(title, createdAt, messages) {
    let md = `# ${title}\n\n`;
    md += `**创建时间**: ${createdAt}\n`;
    md += `**导出时间**: ${new Date().toLocaleString('zh-CN')}\n`;
    md += `**消息数量**: ${messages.length}\n\n`;
    md += `---\n\n`;

    messages.forEach((msg, index) => {
        const role = msg.role === 'user' ? '👤 用户' : '🤖 小乐AI';
        const timestamp = msg.timestamp || msg.created_at || '';

        md += `## ${role}\n\n`;
        if (timestamp) {
            md += `*${timestamp}*\n\n`;
        }
        md += `${msg.content}\n\n`;

        if (index < messages.length - 1) {
            md += `---\n\n`;
        }
    });

    return md;
}

/**
 * 清理文件名（移除非法字符）
 */
function sanitizeFilename(name) {
    return name
        .replace(/[<>:"/\\|?*]/g, '') // 移除Windows非法字符
        .replace(/\s+/g, '_')         // 空格替换为下划线
        .substring(0, 50);            // 限制长度
}

/**
 * 获取时间戳字符串（用于文件名）
 */
function getTimestamp() {
    const now = new Date();
    return now.toISOString()
        .replace(/[:.]/g, '-')
        .replace('T', '_')
        .substring(0, 19);
}

/**
 * 下载文件到本地
 */
function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 加载指定会话
async function loadSession(sessionId) {
    console.log('正在加载会话:', sessionId);

    try {
        const response = await fetch(`${API_BASE}/session/${sessionId}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('会话数据:', data);

        if (data.error) {
            throw new Error(data.error);
        }

        currentSessionId = sessionId;
        const container = document.getElementById('chatContainer');
        container.innerHTML = '';

        // 显示会话信息
        const sessionInfo = document.getElementById('sessionInfo');
        const titleSpan = document.getElementById('currentSessionTitle');
        titleSpan.textContent = data.title || '未命名会话';
        sessionInfo.style.display = 'block';

        // 加载历史消息
        const messages = data.messages || data.history || [];
        if (messages.length > 0) {
            messages.forEach(msg => {
                // 传递 image_path 参数，历史消息不播放语音
                addMessage(msg.role, msg.content, null, msg.image_path, false);
            });
        }

        // 切换到聊天标签页
        switchTab('chat');

        // 更新会话列表的active状态
        document.querySelectorAll('.session-item').forEach(item => {
            if (item.getAttribute('data-session-id') === sessionId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        console.log('会话加载成功');
    } catch (error) {
        console.error('加载会话失败:', error);
        alert('加载会话失败: ' + error.message);
    }
}

// 加载记忆统计
async function loadMemoryStats() {
    try {
        const response = await fetch(`${API_BASE}/memory/stats`);
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

// 加载最近记忆
async function loadRecentMemories() {
    console.log('📋 loadRecentMemories 函数被调用');
    const container = document.getElementById('memoryList');
    console.log('📦 容器元素:', container);
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        console.log('🌐 发起请求: /memory/recent');
        const response = await fetch(`${API_BASE}/memory/recent?hours=24&limit=20`);
        console.log('📡 响应状态:', response.status);
        const data = await response.json();
        console.log('📊 返回数据:', data);

        // API返回的字段是memory，不是memories
        const memories = data.memory || data.memories || [];
        console.log('📋 解析到的记忆数量:', memories.length);

        if (memories.length > 0) {
            container.innerHTML = memories.map(mem => `
                        <div class="memory-item" id="memory-${mem.id}">
                            <div class="memory-content" id="content-${mem.id}">${marked.parse(mem.content)}</div>
                            <div class="memory-meta">
                                <span>🏷️ ${mem.tag}</span>
                                <span>🕐 ${mem.timestamp}</span>
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
                    `).join('');

            // 添加事件监听器
            console.log('🔗 [loadRecentMemories] 开始绑定事件监听器...');
            const editButtons = container.querySelectorAll('.edit-memory-btn');
            const deleteButtons = container.querySelectorAll('.delete-memory-btn');
            console.log(`✅ 找到 ${editButtons.length} 个编辑按钮, ${deleteButtons.length} 个删除按钮`);

            editButtons.forEach(btn => {
                btn.addEventListener('click', function () {
                    console.log('✏️ 编辑按钮被点击, ID:', this.dataset.memoryId);
                    editMemory(this.dataset.memoryId, this.dataset.memoryTag);
                });
            });
            deleteButtons.forEach(btn => {
                btn.addEventListener('click', function () {
                    console.log('🗑️ 删除按钮被点击, ID:', this.dataset.memoryId);
                    deleteMemory(this.dataset.memoryId);
                });
            });
        } else {
            container.innerHTML = '<div class="loading">没有记忆记录</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

// 搜索记忆（关键词）
async function searchMemories() {
    const keywords = document.getElementById('searchInput').value.trim();
    if (!keywords) {
        loadRecentMemories();
        return;
    }

    const container = document.getElementById('memoryList');
    container.innerHTML = '<div class="loading">关键词搜索中...</div>';

    try {
        const response = await fetch(
            `${API_BASE}/memory/search?keywords=${encodeURIComponent(keywords)}&limit=20`
        );
        const data = await response.json();

        if (data.memories && data.memories.length > 0) {
            container.innerHTML = data.memories.map(mem => `
                        <div class="memory-item" id="memory-${mem.id}">
                            <div class="memory-content" id="content-${mem.id}">${marked.parse(mem.content)}</div>
                            <div class="memory-meta">
                                <span>🏷️ ${mem.tag}</span>
                                <span>🕐 ${mem.timestamp}</span>
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
                    `).join('');

            // 添加事件监听器
            console.log('🔗 [searchMemories] 绑定事件...');
            setTimeout(() => {
                const editButtons = container.querySelectorAll('.edit-memory-btn');
                const deleteButtons = container.querySelectorAll('.delete-memory-btn');
                console.log(`✅ [搜索] 找到 ${editButtons.length} 个编辑, ${deleteButtons.length} 个删除按钮`);

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
            }, 0);
        } else {
            container.innerHTML = '<div class="loading">没有找到相关记忆</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="error">搜索失败: ${error.message}</div>`;
    }
}

// 语义搜索记忆
async function semanticSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        alert('请输入查询内容');
        return;
    }

    const container = document.getElementById('memoryList');
    container.innerHTML = '<div class="loading">🧠 语义搜索中...</div>';

    try {
        const response = await fetch(
            `${API_BASE}/memory/semantic?query=${encodeURIComponent(query)}&limit=20`
        );
        const data = await response.json();

        if (data.memories && data.memories.length > 0) {
            container.innerHTML = data.memories.map(mem => `
                        <div class="memory-item" id="memory-${mem.id}">
                            <div class="memory-content" id="content-${mem.id}">${marked.parse(mem.content)}</div>
                            <div class="memory-meta">
                                <span>🏷️ ${mem.tag}</span>
                                <span>🕐 ${mem.timestamp}</span>
                                <span>📊 相似度: ${(mem.score * 100).toFixed(1)}%</span>
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
                    `).join('');

            // 添加事件监听器
            console.log('🔗 [semanticSearch] 绑定事件...');
            setTimeout(() => {
                const editButtons = container.querySelectorAll('.edit-memory-btn');
                const deleteButtons = container.querySelectorAll('.delete-memory-btn');
                console.log(`✅ [语义] 找到 ${editButtons.length} 个编辑, ${deleteButtons.length} 个删除按钮`);

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
            }, 0);
        } else {
            container.innerHTML = '<div class="loading">没有找到相关记忆</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="error">搜索失败: ${error.message}</div>`;
    }
}

// ============ v0.7.0 记忆管理 CRUD 功能 ============

// 编辑记忆
async function editMemory(memoryId, currentTag) {
    const contentEl = document.getElementById(`content-${memoryId}`);
    const currentContent = contentEl.textContent;

    // 创建编辑表单
    const newContent = prompt('编辑记忆内容:', currentContent);
    if (newContent === null || newContent.trim() === '') {
        return;  // 用户取消或内容为空
    }

    const newTag = prompt('编辑标签 (facts/image/conversation/schedule等):', currentTag);
    if (newTag === null || newTag.trim() === '') {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/memory/${memoryId}`, {
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
            // 刷新列表
            loadRecentMemories();
        } else {
            showNotification('❌ 更新失败: ' + (data.error || '未知错误'), 'error');
        }

    } catch (error) {
        console.error('编辑记忆失败:', error);
        showNotification('❌ 更新失败: 网络错误', 'error');
    }
}

// 删除记忆
async function deleteMemory(memoryId) {
    console.log('🗑️ deleteMemory 被调用, ID:', memoryId);

    if (!confirm('确定要删除这条记忆吗？此操作不可恢复！')) {
        console.log('⚠️ 用户取消删除');
        return;
    }

    console.log('✅ 用户确认删除');
    console.log('📡 发送删除请求...');

    try {
        const response = await fetch(`${API_BASE}/api/memory/${memoryId}`, {
            method: 'DELETE'
        });

        console.log('📡 响应状态:', response.status);

        const data = await response.json();
        console.log('📋 响应数据:', data);

        if (data.success) {
            showNotification('✅ 记忆已删除', 'success');
            // 从DOM中移除
            const memoryEl = document.getElementById(`memory-${memoryId}`);
            if (memoryEl) {
                memoryEl.style.opacity = '0';
                setTimeout(() => memoryEl.remove(), 300);
            }
        } else {
            showNotification('❌ 删除失败: ' + (data.error || '未知错误'), 'error');
        }

    } catch (error) {
        console.error('删除记忆失败:', error);
        showNotification('❌ 删除失败: 网络错误', 'error');
    }
}

// ============ 记忆管理功能结束 ============

// 自动刷新相关变量
let autoRefreshInterval = null;
let lastRefreshTime = null;

// 切换自动刷新
function toggleAutoRefresh() {
    const checkbox = document.getElementById('autoRefreshToggle');
    const statusSpan = document.getElementById('refreshStatus');

    if (checkbox.checked) {
        // 启用自动刷新
        loadBehaviorAnalytics();
        lastRefreshTime = Date.now();
        updateRefreshStatus();

        autoRefreshInterval = setInterval(() => {
            loadBehaviorAnalytics();
            lastRefreshTime = Date.now();
            updateRefreshStatus();
        }, 30000); // 30秒

        statusSpan.style.color = '#51cf66';
        console.log('✅ 自动刷新已启用 (30秒)');
    } else {
        // 禁用自动刷新
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
        statusSpan.textContent = '';
        console.log('⏸️ 自动刷新已禁用');
    }
}

// 更新刷新状态
function updateRefreshStatus() {
    const statusSpan = document.getElementById('refreshStatus');
    if (lastRefreshTime) {
        const now = Date.now();
        const elapsed = Math.floor((now - lastRefreshTime) / 1000);
        statusSpan.textContent = `上次刷新: ${elapsed}秒前`;
    }
}

// 定期更新状态显示
setInterval(() => {
    if (autoRefreshInterval && lastRefreshTime) {
        updateRefreshStatus();
    }
}, 1000);

// 加载行为分析数据
async function loadBehaviorAnalytics() {
    const userId = 'default_user';

    // 加载活跃时间分布
    loadActivityPattern(userId);

    // 加载话题偏好
    loadTopicPreferences(userId);

    // 加载对话统计
    loadBehaviorStats(userId);

    // 加载冲突检测
    loadConflictDetection();

    // 加载主动问答历史
    loadProactiveQA(userId);

    // 加载学习模式
    loadLearningPatterns(userId);
}

// 加载活跃时间分布
async function loadActivityPattern(userId) {
    const container = document.getElementById('activityPattern');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const response = await fetch(`${API_BASE}/analytics/activity?user_id=${userId}`);
        const data = await response.json();

        if (data.error) {
            container.innerHTML = '<div style="color: #999;">暂无数据</div>';
            return;
        }

        let html = '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">';

        // 小时分布
        if (data.hourly_distribution && Object.keys(data.hourly_distribution).length > 0) {
            html += '<div><strong>📅 活跃时段（小时）</strong><div style="margin-top: 8px;">';
            const sortedHours = Object.entries(data.hourly_distribution).sort((a, b) => b[1] - a[1]).slice(0, 5);
            sortedHours.forEach(([hour, count]) => {
                html += `<div style="margin: 5px 0;">🕐 ${hour}:00 - ${count}次</div>`;
            });
            html += '</div></div>';
        }

        // 星期分布
        if (data.daily_distribution && Object.keys(data.daily_distribution).length > 0) {
            const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
            html += '<div><strong>📆 活跃星期</strong><div style="margin-top: 8px;">';
            const sortedDays = Object.entries(data.daily_distribution).sort((a, b) => b[1] - a[1]);
            sortedDays.forEach(([day, count]) => {
                html += `<div style="margin: 5px 0;">${weekdays[day] || '周' + day} - ${count}次</div>`;
            });
            html += '</div></div>';
        }

        html += '</div>';
        container.innerHTML = html || '<div style="color: #999;">暂无数据</div>';
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

// 加载话题偏好
async function loadTopicPreferences(userId) {
    const container = document.getElementById('topicPreferences');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const response = await fetch(`${API_BASE}/analytics/topics?user_id=${userId}`);
        const data = await response.json();

        if (data.error || !data.top_topics || data.top_topics.length === 0) {
            container.innerHTML = '<div style="color: #999;">暂无话题数据</div>';
            return;
        }

        let html = '<div>';
        data.top_topics.slice(0, 10).forEach((item, index) => {
            const [topic, count] = item;
            html += `
                        <div style="margin: 8px 0; padding: 8px; background: white; border-radius: 5px; display: flex; justify-content: space-between; align-items: center;">
                            <span>${index + 1}. 🏷️ ${topic}</span>
                            <span style="color: #667eea; font-weight: bold;">${count}次</span>
                        </div>
                    `;
        });
        html += '</div>';

        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

// 加载对话统计
async function loadBehaviorStats(userId) {
    const container = document.getElementById('behaviorStats');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const response = await fetch(`${API_BASE}/analytics/behavior?user_id=${userId}`);
        const data = await response.json();

        if (data.error) {
            container.innerHTML = '<div style="color: #999;">暂无数据</div>';
            return;
        }

        // 修复：使用 conversation_stats 而不是 stats
        const stats = data.conversation_stats || {};
        let html = `
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        <div style="text-align: center; padding: 10px; background: white; border-radius: 8px;">
                            <div style="font-size: 24px; font-weight: bold; color: #667eea;">${stats.total_sessions || 0}</div>
                            <div style="color: #999; margin-top: 5px;">总会话数</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: white; border-radius: 8px;">
                            <div style="font-size: 24px; font-weight: bold; color: #667eea;">${stats.total_messages || 0}</div>
                            <div style="color: #999; margin-top: 5px;">总消息数</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: white; border-radius: 8px;">
                            <div style="font-size: 24px; font-weight: bold; color: #667eea;">${stats.avg_messages_per_session || 0}</div>
                            <div style="color: #999; margin-top: 5px;">平均消息/会话</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: white; border-radius: 8px;">
                            <div style="font-size: 24px; font-weight: bold; color: #667eea;">${stats.avg_message_length || 0}</div>
                            <div style="color: #999; margin-top: 5px;">平均消息长度</div>
                        </div>
                    </div>
                `;

        if (stats.last_session_time) {
            html += `<div style="margin-top: 15px; text-align: center; color: #666;">
                        最后活跃: ${new Date(stats.last_session_time).toLocaleString('zh-CN')}
                    </div>`;
        }

        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

// 加载冲突检测
async function loadConflictDetection() {
    const container = document.getElementById('conflictDetection');
    container.innerHTML = '<div class="loading">检测中...</div>';

    try {
        const response = await fetch(`${API_BASE}/memory/conflicts`);
        const data = await response.json();

        if (data.conflicts && data.conflicts.length > 0) {
            let html = `<div style="color: #ff6b6b; font-weight: bold; margin-bottom: 10px;">
                        ⚠️ 发现 ${data.conflicts.length} 组冲突记忆
                    </div>`;

            data.conflicts.forEach((conflict, index) => {
                html += `
                            <div style="margin: 10px 0; padding: 10px; background: white; border-left: 3px solid #ff6b6b; border-radius: 5px;">
                                <div style="font-weight: bold; margin-bottom: 5px;">冲突 ${index + 1}: ${conflict.type_cn}</div>
                                <div style="margin: 5px 0; padding: 5px; background: #fff5f5; border-radius: 3px;">
                                    📄 旧值: ${conflict.old_value} - ${conflict.old_memory}
                                </div>
                                <div style="margin: 5px 0; padding: 5px; background: #fff5f5; border-radius: 3px;">
                                    📄 新值: ${conflict.new_value} - ${conflict.new_memory}
                                </div>
                                <div style="margin-top: 5px; color: #999; font-size: 12px;">
                                    检测时间: ${conflict.conflict_detected_at}
                                </div>
                            </div>
                        `;
            });

            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="color: #51cf66; text-align: center;">✅ 没有发现冲突记忆</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="error">检测失败: ${error.message}</div>`;
    }
}

// 加载主动问答历史
async function loadProactiveQA(userId) {
    const container = document.getElementById('proactiveQA');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const response = await fetch(`${API_BASE}/proactive/history?user_id=${userId}&limit=10`);
        const data = await response.json();

        if (data.history && data.history.length > 0) {
            let html = `<div style="color: #764ba2; font-weight: bold; margin-bottom: 10px;">
                        💡 共 ${data.total} 条追问记录（显示最近10条）
                    </div>`;

            data.history.forEach((item, index) => {
                const confidenceColor = item.confidence >= 70 ? '#51cf66' : item.confidence >= 50 ? '#ffd43b' : '#ff6b6b';
                const askedBadge = item.followup_asked
                    ? '<span style="background: #51cf66; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">已追问</span>'
                    : '<span style="background: #999; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">待追问</span>';

                // 待追问的记录显示发送按钮
                const actionButton = !item.followup_asked
                    ? `<button class="send-followup-btn" data-id="${item.id}" data-text="${item.followup_question.replace(/"/g, '&quot;')}" data-user="${userId}"
                                style="margin-top: 8px; padding: 6px 12px; background: #764ba2; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">
                                📤 发送追问
                               </button>`
                    : '';

                html += `
                            <div style="margin: 10px 0; padding: 12px; background: white; border-left: 3px solid #764ba2; border-radius: 5px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <span style="font-weight: bold;">记录 ${index + 1}</span>
                                    <div style="display: flex; gap: 5px; align-items: center;">
                                        ${askedBadge}
                                        <span style="background: ${confidenceColor}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">
                                            置信度 ${item.confidence}%
                                        </span>
                                    </div>
                                </div>
                                <div style="margin: 5px 0; padding: 8px; background: #f8f4ff; border-radius: 3px;">
                                    <div style="font-size: 12px; color: #999; margin-bottom: 3px;">原始问题:</div>
                                    <div>❓ ${item.original_question}</div>
                                </div>
                                <div style="margin: 5px 0; padding: 8px; background: #e7f5ff; border-radius: 3px;">
                                    <div style="font-size: 12px; color: #999; margin-bottom: 3px;">建议追问:</div>
                                    <div>💬 ${item.followup_question}</div>
                                </div>
                                <div style="margin-top: 5px; color: #999; font-size: 11px;">
                                    创建时间: ${new Date(item.created_at).toLocaleString('zh-CN')}
                                    ${item.asked_at ? ` | 追问时间: ${new Date(item.asked_at).toLocaleString('zh-CN')}` : ''}
                                </div>
                                ${actionButton}
                            </div>
                        `;
            });

            container.innerHTML = html;

            // 为所有发送按钮添加事件监听器
            container.querySelectorAll('.send-followup-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    const id = this.getAttribute('data-id');
                    const text = this.getAttribute('data-text');
                    const user = this.getAttribute('data-user');
                    sendFollowupFromHistory(id, text, user);
                });
            });
        } else {
            container.innerHTML = '<div style="color: #999; text-align: center;">暂无追问记录</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

// 加载学习模式
async function loadLearningPatterns(userId) {
    const container = document.getElementById('learningPatterns');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        // 并行获取三个API数据
        const [frequentRes, questionsRes, insightsRes] = await Promise.all([
            fetch(`${API_BASE}/patterns/frequent?user_id=${userId}&limit=10`),
            fetch(`${API_BASE}/patterns/common_questions?user_id=${userId}&limit=5`),
            fetch(`${API_BASE}/patterns/insights?user_id=${userId}`)
        ]);

        const frequentData = await frequentRes.json();
        const questionsData = await questionsRes.json();
        const insightsData = await insightsRes.json();

        let html = '';

        // 显示统计概览
        if (insightsData && insightsData.statistics) {
            const stats = insightsData.statistics;
            html += `<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 15px;">`;
            html += `<div style="background: white; padding: 10px; border-radius: 5px; text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: #10b981;">${stats.total_patterns || 0}</div>
                        <div style="font-size: 12px; color: #999;">总学习模式</div>
                    </div>`;
            html += `<div style="background: white; padding: 10px; border-radius: 5px; text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: #10b981;">${stats.frequent_words_count || 0}</div>
                        <div style="font-size: 12px; color: #999;">高频词汇</div>
                    </div>`;
            html += `<div style="background: white; padding: 10px; border-radius: 5px; text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: #10b981;">${stats.common_questions_count || 0}</div>
                        <div style="font-size: 12px; color: #999;">常见问题</div>
                    </div>`;
            html += `</div>`;
        }

        // 显示高频词
        if (frequentData.frequent_words && frequentData.frequent_words.length > 0) {
            html += `<div style="margin: 15px 0;">
                        <div style="font-weight: bold; color: #10b981; margin-bottom: 8px;">📝 高频词汇 TOP10</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">`;

            frequentData.frequent_words.forEach(item => {
                const confidence = item.confidence || 50;
                const bgColor = confidence >= 80 ? '#10b981' : confidence >= 60 ? '#3b82f6' : '#6b7280';
                html += `<span style="background: ${bgColor}; color: white; padding: 5px 12px; border-radius: 15px; font-size: 13px;">
                            ${item.word} (${item.frequency}次)
                        </span>`;
            });

            html += `</div></div>`;
        }

        // 显示常见问题分类
        if (questionsData.common_questions && questionsData.common_questions.length > 0) {
            html += `<div style="margin: 15px 0;">
                        <div style="font-weight: bold; color: #10b981; margin-bottom: 8px;">❓ 常见问题分类</div>`;

            questionsData.common_questions.forEach(item => {
                const typeEmoji = {
                    '天气查询': '🌤️',
                    '时间日期': '⏰',
                    '个人信息': '👤',
                    '功能咨询': '🔧',
                    '推荐建议': '💡',
                    '闲聊': '💬'
                };

                html += `<div style="margin: 10px 0; padding: 10px; background: white; border-left: 3px solid #10b981; border-radius: 5px;">
                            <div style="font-weight: bold; margin-bottom: 5px;">
                                ${typeEmoji[item.category] || '📌'} ${item.category} 
                                <span style="color: #999; font-size: 12px; font-weight: normal;">(${item.frequency}次)</span>
                            </div>`;

                if (item.examples && item.examples.length > 0) {
                    html += `<div style="font-size: 12px; color: #666; margin-top: 5px;">`;
                    item.examples.slice(0, 2).forEach(example => {
                        html += `<div style="margin: 3px 0;">• ${example}</div>`;
                    });
                    html += `</div>`;
                }

                html += `</div>`;
            });

            html += `</div>`;
        }

        if (!html) {
            html = '<div style="color: #999; text-align: center;">暂无学习数据，多聊几句让小乐了解你吧~</div>';
        }

        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

// ============ 工具管理功能已迁移至 modules/tools.js ============

// ============ v0.8.0 任务管理功能 ============

// HTML转义函数，防止XSS攻击
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 加载任务列表
async function loadTasks() {
    const container = document.getElementById('tasksList');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const statusFilter = document.getElementById('taskStatusFilter').value;
        const userId = 'default_user'; // 使用默认用户ID

        let url = `${API_BASE}/api/users/${userId}/tasks?limit=50`;
        if (statusFilter) {
            url += `&status=${statusFilter}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '加载任务失败');
        }

        const tasks = data.tasks || [];

        // 更新统计
        updateTaskStats(tasks);

        if (tasks.length === 0) {
            container.innerHTML = '<div class="loading">暂无任务</div>';
            return;
        }

        // 按优先级和状态排序
        tasks.sort((a, b) => {
            if (a.priority !== b.priority) return b.priority - a.priority;
            if (a.status !== b.status) {
                const order = ['in_progress', 'pending', 'waiting', 'failed', 'completed', 'cancelled'];
                return order.indexOf(a.status) - order.indexOf(b.status);
            }
            return new Date(b.created_at) - new Date(a.created_at);
        });

        // 渲染任务卡片
        let html = '<div>';
        tasks.forEach(task => {
            html += renderTaskCard(task);
        });
        html += '</div>';
        container.innerHTML = html;

    } catch (error) {
        console.error('加载任务失败:', error);
        container.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
    }
}

// 渲染任务卡片
function renderTaskCard(task) {
    const statusMap = {
        'pending': '待处理',
        'in_progress': '执行中',
        'waiting': '等待中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消'
    };

    const priorityMap = {
        0: '普通',
        1: '重要',
        2: '紧急'
    };

    const progress = task.total_steps > 0
        ? Math.round((task.current_step / task.total_steps) * 100)
        : 0;

    const statusClass = task.status;
    const statusText = statusMap[task.status] || task.status;
    const priorityClass = `priority-${task.priority}`;
    const priorityText = priorityMap[task.priority] || '普通';

    const createdTime = new Date(task.created_at).toLocaleString('zh-CN');
    const updatedTime = task.updated_at ? new Date(task.updated_at).toLocaleString('zh-CN') : '-';

    return `
                <div class="task-card status-${statusClass}">
                    <div class="task-header">
                        <div style="flex: 1;">
                            <div class="task-title">${escapeHtml(task.title)}</div>
                            ${task.description ? `<div class="task-description">${escapeHtml(task.description)}</div>` : ''}
                        </div>
                        <div style="display: flex; gap: 8px; align-items: flex-start;">
                            <span class="priority-badge ${priorityClass}">${priorityText}</span>
                            <span class="task-status-badge ${statusClass}">${statusText}</span>
                        </div>
                    </div>

                    ${task.total_steps > 0 ? `
                    <div class="task-progress">
                        <div class="task-progress-bar">
                            <div class="task-progress-fill" style="width: ${progress}%"></div>
                        </div>
                        <div class="task-progress-text">${task.current_step}/${task.total_steps}</div>
                    </div>
                    ` : ''}

                    <div class="task-meta">
                        <span>📅 创建: ${createdTime}</span>
                        <span>🔄 更新: ${updatedTime}</span>
                        ${task.retry_count > 0 ? `<span>🔁 重试: ${task.retry_count}次</span>` : ''}
                    </div>

                    <div class="task-actions">
                        <button class="task-btn task-btn-primary" onclick="showTaskDetails(${task.id})">📋 详情</button>
                        ${task.status === 'pending' || task.status === 'waiting' ? `
                        <button class="task-btn task-btn-success" onclick="executeTask(${task.id})">▶️ 执行</button>
                        ` : ''}
                        ${task.status === 'in_progress' || task.status === 'waiting' ? `
                        <button class="task-btn task-btn-secondary" onclick="cancelTask(${task.id})">⏸️ 取消</button>
                        ` : ''}
                        ${task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled' ? `
                        <button class="task-btn task-btn-danger" onclick="deleteTask(${task.id})">🗑️ 删除</button>
                        ` : ''}
                    </div>
                </div>
            `;
}

// 更新任务统计
function updateTaskStats(tasks) {
    const stats = {
        pending: 0,
        in_progress: 0,
        completed: 0,
        failed: 0
    };

    tasks.forEach(task => {
        if (stats.hasOwnProperty(task.status)) {
            stats[task.status]++;
        }
    });

    document.getElementById('taskPendingCount').textContent = stats.pending;
    document.getElementById('taskInProgressCount').textContent = stats.in_progress;
    document.getElementById('taskCompletedCount').textContent = stats.completed;
    document.getElementById('taskFailedCount').textContent = stats.failed;
}

// 显示任务详情
async function showTaskDetails(taskId) {
    try {
        const response = await fetch(`${API_BASE}/api/tasks/${taskId}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '获取任务详情失败');
        }

        const task = data.task;
        const steps = data.steps || [];

        let stepsHtml = '';
        if (steps.length > 0) {
            stepsHtml = '<div style="margin-top: 15px;"><h4>任务步骤:</h4>';
            steps.forEach((step, index) => {
                const stepStatus = step.status || 'pending';
                const stepClass = stepStatus === 'completed' ? 'completed' : (stepStatus === 'failed' ? 'failed' : '');
                stepsHtml += `
                            <div class="task-step ${stepClass}">
                                <div class="task-step-header">
                                    <span class="task-step-title">${index + 1}. ${escapeHtml(step.description)}</span>
                                    <span class="task-step-status">${stepStatus}</span>
                                </div>
                                ${step.action_type ? `<div style="font-size: 12px; color: #6b7280; margin-top: 5px;">类型: ${step.action_type}</div>` : ''}
                                ${step.error ? `<div style="font-size: 12px; color: #ef4444; margin-top: 5px;">错误: ${escapeHtml(step.error)}</div>` : ''}
                            </div>
                        `;
            });
            stepsHtml += '</div>';
        }

        const detailHtml = `
                    <div style="max-width: 600px;">
                        <h3>${escapeHtml(task.title)}</h3>
                        ${task.description ? `<p style="color: #6b7280; margin: 10px 0;">${escapeHtml(task.description)}</p>` : ''}
                        
                        <div style="margin: 15px 0; padding: 15px; background: #f3f4f6; border-radius: 8px;">
                            <div><strong>状态:</strong> ${task.status}</div>
                            <div><strong>优先级:</strong> ${task.priority}</div>
                            <div><strong>进度:</strong> ${task.current_step}/${task.total_steps}</div>
                            <div><strong>创建时间:</strong> ${new Date(task.created_at).toLocaleString('zh-CN')}</div>
                            ${task.started_at ? `<div><strong>开始时间:</strong> ${new Date(task.started_at).toLocaleString('zh-CN')}</div>` : ''}
                            ${task.completed_at ? `<div><strong>完成时间:</strong> ${new Date(task.completed_at).toLocaleString('zh-CN')}</div>` : ''}
                        </div>

                        ${stepsHtml}
                    </div>
                `;

        // 使用现有的通知弹窗显示详情
        showCustomNotification('任务详情', detailHtml);

    } catch (error) {
        console.error('获取任务详情失败:', error);
        showNotification('❌ 获取任务详情失败', 'error');
    }
}

// 执行任务
async function executeTask(taskId) {
    if (!confirm('确定要执行这个任务吗?')) return;

    try {
        const response = await fetch(`${API_BASE}/api/tasks/${taskId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: 'default_user',
                session_id: currentSessionId || ''
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '执行任务失败');
        }

        showNotification('✅ 任务执行成功', 'success');
        loadTasks(); // 刷新列表

    } catch (error) {
        console.error('执行任务失败:', error);
        showNotification(`❌ 执行失败: ${error.message}`, 'error');
    }
}

// 取消任务
async function cancelTask(taskId) {
    if (!confirm('确定要取消这个任务吗?')) return;

    try {
        const response = await fetch(`${API_BASE}/api/tasks/${taskId}/cancel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '取消任务失败');
        }

        showNotification('✅ 任务已取消', 'success');
        loadTasks(); // 刷新列表

    } catch (error) {
        console.error('取消任务失败:', error);
        showNotification(`❌ 取消失败: ${error.message}`, 'error');
    }
}

// 删除任务
async function deleteTask(taskId) {
    if (!confirm('确定要删除这个任务吗? 此操作不可恢复!')) return;

    try {
        const response = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '删除任务失败');
        }

        showNotification('✅ 任务已删除', 'success');
        loadTasks(); // 刷新列表

    } catch (error) {
        console.error('删除任务失败:', error);
        showNotification(`❌ 删除失败: ${error.message}`, 'error');
    }
}

// 显示创建任务对话框
function showCreateTaskDialog() {
    const html = `
                <div style="max-width: 500px;">
                    <h3>创建新任务</h3>
                    <div style="margin: 15px 0;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 500;">任务标题:</label>
                        <input type="text" id="newTaskTitle" placeholder="输入任务标题" 
                            style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 8px;">
                    </div>
                    <div style="margin: 15px 0;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 500;">任务描述:</label>
                        <textarea id="newTaskDesc" placeholder="输入任务描述（可选）" rows="3"
                            style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 8px; resize: vertical;"></textarea>
                    </div>
                    <div style="margin: 15px 0;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 500;">优先级:</label>
                        <select id="newTaskPriority" style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 8px;">
                            <option value="0">普通</option>
                            <option value="1">重要</option>
                            <option value="2">紧急</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 20px;">
                        <button onclick="createTask()" style="flex: 1; padding: 12px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;">
                            ✅ 创建
                        </button>
                        <button onclick="closeCustomNotification()" style="flex: 1; padding: 12px; background: #6b7280; color: white; border: none; border-radius: 8px; cursor: pointer;">
                            ❌ 取消
                        </button>
                    </div>
                </div>
            `;
    showCustomNotification('创建任务', html);
}

// 创建任务
async function createTask() {
    const title = document.getElementById('newTaskTitle').value.trim();
    const description = document.getElementById('newTaskDesc').value.trim();
    const priority = parseInt(document.getElementById('newTaskPriority').value);

    if (!title) {
        showNotification('❌ 请输入任务标题', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: 'default_user',
                session_id: currentSessionId || '',
                title: title,
                description: description,
                priority: priority
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '创建任务失败');
        }

        showNotification('✅ 任务创建成功', 'success');
        closeCustomNotification();
        loadTasks(); // 刷新列表

    } catch (error) {
        console.error('创建任务失败:', error);
        showNotification(`❌ 创建失败: ${error.message}`, 'error');
    }
}

// 显示自定义通知弹窗
function showCustomNotification(title, content) {
    // 移除已存在的弹窗
    const existing = document.querySelector('.custom-notification-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'custom-notification-overlay';
    overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10001;
            `;

    const modal = document.createElement('div');
    modal.style.cssText = `
                background: var(--card-bg);
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 8px 24px var(--shadow-heavy);
                max-width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            `;
    modal.innerHTML = content;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // 点击overlay关闭
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeCustomNotification();
        }
    });
}

// 关闭自定义通知
function closeCustomNotification() {
    const overlay = document.querySelector('.custom-notification-overlay');
    if (overlay) overlay.remove();
}

// ============ v0.8.0 任务管理功能结束 ============

// ============ 课程表管理功能已迁移至 modules/schedule.js ============// ============ WebSocket实时推送 ============
let ws = null;
let wsReconnectTimer = null;
let unreadReminderCount = 0;

function connectWebSocket() {
    try {
        // 建立WebSocket连接
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('✅ WebSocket已连接');
            clearTimeout(wsReconnectTimer);

            // 发送心跳
            setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 30000); // 每30秒发送心跳
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === 'proactive_chat') {
                    // 收到主动对话推送
                    handleProactiveChatPush(message);
                } else if (message.type === 'pong') {
                    // 心跳响应
                    console.log('心跳响应');
                }
            } catch (error) {
                console.error('解析WebSocket消息失败:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };

        ws.onclose = () => {
            console.log('❌ WebSocket已断开，5秒后重连...');
            wsReconnectTimer = setTimeout(connectWebSocket, 5000);
        };

    } catch (error) {
        console.error('WebSocket连接失败:', error);
        wsReconnectTimer = setTimeout(connectWebSocket, 5000);
    }
}

// ============ 主动对话处理 ============

function handleProactiveChatPush(message) {
    console.log('收到主动对话推送:', message);

    // 播放柔和的提示音（不同于提醒的声音）
    playProactiveChatSound();

    // 显示主动对话通知
    showProactiveChatNotification(message);

    // 如果页面不在前台，发送浏览器通知
    if (document.hidden) {
        sendProactiveChatBrowserNotification(message);
    }
}

function playProactiveChatSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        // 更柔和的音调（600Hz）
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(600, audioContext.currentTime);

        // 渐变音量
        gainNode.gain.setValueAtTime(0, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.2, audioContext.currentTime + 0.15);
        gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.6);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.6);
    } catch (error) {
        console.error('播放主动对话提示音失败:', error);
    }
}

function showProactiveChatNotification(message) {
    // 创建主动对话通知卡片
    const notification = document.createElement('div');
    notification.className = 'proactive-chat-notification';
    notification.style.cssText = `
                position: fixed;
                bottom: 30px;
                right: 30px;
                max-width: 400px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                z-index: 10000;
                animation: slideInRight 0.3s ease-out;
            `;

    const reasonEmoji = {
        'pending_question': '🤔',
        'long_inactive': '👋',
        'moderate_inactive': '💭',
        'active_time': '⏰',
        'interesting_topic': '💡'
    };

    const emoji = reasonEmoji[message.reason] || '💬';

    notification.innerHTML = `
                <div style="display: flex; align-items: flex-start; gap: 15px;">
                    <div style="font-size: 32px;">${emoji}</div>
                    <div style="flex: 1;">
                        <div style="font-weight: bold; font-size: 16px; margin-bottom: 10px;">
                            小乐想和你聊聊～
                        </div>
                        <div style="font-size: 14px; line-height: 1.6; margin-bottom: 15px;">
                            ${message.message}
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <button onclick="respondToProactiveChat('${message.reason}')" 
                                style="flex: 1; background: white; color: #667eea; border: none; padding: 10px; border-radius: 8px; font-weight: bold; cursor: pointer;">
                                💬 去聊天
                            </button>
                            <button onclick="dismissProactiveChat(this)" 
                                style="background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 15px; border-radius: 8px; cursor: pointer;">
                                稍后
                            </button>
                        </div>
                    </div>
                </div>
            `;

    document.body.appendChild(notification);

    // 10秒后自动消失
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }
    }, 10000);
}

function respondToProactiveChat(reason) {
    // 关闭通知
    const notification = document.querySelector('.proactive-chat-notification');
    if (notification) {
        notification.remove();
    }

    // 切换到聊天标签
    switchTab('chat');

    // 聚焦输入框
    const messageInput = document.getElementById('messageInput');
    messageInput.focus();

    // 可以根据reason预填充一些内容
    // messageInput.textContent = '';
}

function dismissProactiveChat(button) {
    const notification = button.closest('.proactive-chat-notification');
    if (notification) {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }
}

function sendProactiveChatBrowserNotification(message) {
    if ('Notification' in window && Notification.permission === 'granted') {
        const reasonText = {
            'pending_question': '关于之前的问题',
            'long_inactive': '好久不见',
            'moderate_inactive': '最近还好吗',
            'active_time': '问候时间',
            'interesting_topic': '有趣的话题'
        };

        new Notification('小乐想和你聊聊', {
            body: message.message,
            icon: '/static/icon.png',
            tag: 'proactive-chat',
            requireInteraction: false
        });
    }
}

// 显示追问提示
function showFollowupSuggestion(followupInfo) {
    // 创建追问提示卡片
    const notification = document.createElement('div');
    notification.className = 'followup-suggestion';
    notification.style.cssText = `
                position: fixed;
                bottom: 30px;
                left: 50%;
                transform: translateX(-50%);
                max-width: 500px;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                padding: 18px 24px;
                border-radius: 12px;
                box-shadow: 0 8px 24px rgba(245, 87, 108, 0.4);
                z-index: 10000;
                animation: slideInUp 0.3s ease-out;
                cursor: pointer;
            `;

    notification.innerHTML = `
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="font-size: 24px;">🤔</div>
                    <div style="flex: 1;">
                        <div style="font-size: 13px; opacity: 0.9; margin-bottom: 4px;">
                            💡 小乐有个疑问
                        </div>
                        <div style="font-size: 15px; font-weight: 500; line-height: 1.5;">
                            ${followupInfo.followup}
                        </div>
                    </div>
                    <div style="font-size: 12px; opacity: 0.8;">
                        点击回答
                    </div>
                </div>
            `;

    // 点击发送追问
    notification.onclick = async () => {
        notification.remove();

        // 自动发送追问作为用户消息
        const input = document.getElementById('messageInput');
        input.textContent = followupInfo.followup;

        // 发送消息
        await sendMessageFromDiv();

        // 标记追问已发送
        try {
            await fetch(`${API_BASE}/proactive/mark_asked/${followupInfo.id}`, {
                method: 'POST'
            });
            // 刷新主动问答列表
            loadProactiveQA('default_user');
        } catch (error) {
            console.error('标记追问失败:', error);
        }
    };

    document.body.appendChild(notification);

    // 播放提示音
    playFollowupSound();

    // 8秒后自动消失
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutDown 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }
    }, 8000);
}

// 播放追问提示音
function playFollowupSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = 800;  // 更高音调
        oscillator.type = 'sine';

        gainNode.gain.setValueAtTime(0, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.1, audioContext.currentTime + 0.01);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.15);
    } catch (error) {
        console.error('播放追问提示音失败:', error);
    }
}

// 从历史记录发送追问
async function sendFollowupFromHistory(questionId, followupText, userId) {
    // 自动填充到输入框
    const input = document.getElementById('messageInput');
    input.textContent = followupText;

    // 发送消息
    await sendMessageFromDiv();

    // 标记为已追问
    try {
        await fetch(`${API_BASE}/proactive/mark_asked/${questionId}`, {
            method: 'POST'
        });
        // 刷新主动问答列表
        setTimeout(() => loadProactiveQA(userId), 1000);
    } catch (error) {
        console.error('标记追问失败:', error);
    }
}

// ============ WebSocket功能结束 ============

// ============ v0.6.0 全局快捷键支持 ============

// 全局快捷键监听
document.addEventListener('keydown', (event) => {
    // 检查快捷键是否启用
    const settings = getSettings();
    if (!settings.keyboardShortcuts) {
        return; // 快捷键已禁用，直接返回
    }

    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const ctrlKey = isMac ? event.metaKey : event.ctrlKey;

    // 空格键: 在连续对话模式下打断AI说话
    if (event.code === 'Space' && isConversationMode && isSpeaking && !isRecording) {
        // 确保不是在输入框中按空格
        if (document.activeElement.tagName !== 'INPUT' &&
            document.activeElement.id !== 'messageInput') {
            event.preventDefault();
            console.log('⌨️ 按空格键打断AI');
            stopSpeaking();
            // 立即开始录音
            setTimeout(() => {
                if (isConversationMode && !isRecording) {
                    toggleBaiduVoiceInput();
                }
            }, 100);
            return;
        }
    }

    // Ctrl+Enter / Cmd+Enter: 发送消息
    if (ctrlKey && event.key === 'Enter') {
        event.preventDefault();
        const currentTab = document.querySelector('.tab-content.active');
        if (currentTab && currentTab.id === 'chat') {
            sendMessageFromDiv();
        }
        return;
    }

    // Esc: 清空输入框
    if (event.key === 'Escape') {
        const messageInput = document.getElementById('messageInput');
        if (messageInput && document.activeElement === messageInput) {
            event.preventDefault();
            messageInput.textContent = '';
            messageInput.focus();
        }
        return;
    }

    // Ctrl+K / Cmd+K: 新建对话
    if (ctrlKey && event.key === 'k') {
        event.preventDefault();
        newChat();
        return;
    }

    // Ctrl+/ / Cmd+/: 切换到聊天标签
    if (ctrlKey && event.key === '/') {
        event.preventDefault();
        const chatTab = document.querySelector('[onclick*="chat"]');
        if (chatTab) {
            chatTab.click();
        }
        return;
    }

    // Ctrl+1-6 / Cmd+1-6: 快速切换标签
    if (ctrlKey && event.key >= '1' && event.key <= '6') {
        event.preventDefault();
        const tabs = ['chat', 'sessions', 'memory', 'analytics', 'reminders', 'tools'];
        const tabIndex = parseInt(event.key) - 1;
        if (tabIndex < tabs.length) {
            const tabButton = document.querySelector(`[onclick*="${tabs[tabIndex]}"]`);
            if (tabButton) {
                tabButton.click();
            }
        }
        return;
    }
});

// 显示快捷键提示（鼠标悬停在输入框时）
function showShortcutHints() {
    const messageInput = document.getElementById('messageInput');
    const hintsBar = document.getElementById('shortcutHints');
    if (!messageInput || !hintsBar) return;

    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const cmdKey = isMac ? '⌘' : 'Ctrl';

    // 更新Mac系统的快捷键显示
    if (isMac) {
        hintsBar.querySelectorAll('kbd').forEach(kbd => {
            kbd.textContent = kbd.textContent.replace('Ctrl', '⌘');
        });
    }

    // 输入框聚焦时显示提示栏
    messageInput.addEventListener('focus', () => {
        hintsBar.style.opacity = '1';
    });

    // 输入框失焦时隐藏提示栏（延迟隐藏）
    messageInput.addEventListener('blur', () => {
        setTimeout(() => {
            hintsBar.style.opacity = '0';
        }, 2000);
    });

    // 页面加载后3秒显示提示栏（首次提示）
    setTimeout(() => {
        hintsBar.style.opacity = '1';
        setTimeout(() => {
            hintsBar.style.opacity = '0';
        }, 3000);
    }, 1000);
}        // ============ 快捷键功能结束 ============

// 页面加载时聚焦输入框
window.onload = () => {
    const messageInput = document.getElementById('messageInput');
    messageInput.focus();

    // 显示快捷键提示
    showShortcutHints();

    // 自动加载历史对话列表
    loadSessions();

    // 图片上传事件监听器（额外添加以确保捕获）
    const imageUploadInput = document.getElementById('imageUpload');
    if (imageUploadInput) {
        console.log('✅ 图片上传input已找到，添加事件监听器');
        imageUploadInput.addEventListener('change', (event) => {
            console.log('🎯 Change event triggered (addEventListener)');
            handleImageUpload(event);
        });
        imageUploadInput.addEventListener('cancel', () => {
            console.log('❌ 用户取消了文件选择');
        });
    } else {
        console.error('❌ 未找到图片上传input元素！');
    }

    // Enter发送，Shift+Enter换行
    messageInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessageFromDiv();
        }
    });

    // 搜索框回车搜索
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                searchMemories();
            }
        });
    }

    // 建立WebSocket连接
    connectWebSocket();

    // 请求浏览器通知权限
    requestNotificationPermission();

    // 预加载音频（激活音频权限）
    const preloadAudio = new Audio('/static/sounds/dingdong.mp3');
    preloadAudio.volume = 0.01; // 极小音量
    // 在用户第一次点击页面时播放（激活权限）
    document.addEventListener('click', function initAudio() {
        preloadAudio.play().then(() => {
            console.log('✅ 音频权限已激活');
            preloadAudio.pause();
            preloadAudio.currentTime = 0;
        }).catch(e => {
            console.warn('音频权限激活失败:', e);
        });
        // 只执行一次
        document.removeEventListener('click', initAudio);
    }, { once: true });
};

// ========================================
// v0.6.0 Phase 4: 图片上传和识别功能
// ========================================
let uploadedImagePath = null;

/**
 * 显示通知消息
 */
function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);

    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                font-size: 14px;
                max-width: 300px;
                animation: slideInRight 0.3s ease-out;
                ${type === 'success' ? 'background: #10b981; color: white;' : ''}
                ${type === 'error' ? 'background: #ef4444; color: white;' : ''}
                ${type === 'info' ? 'background: #3b82f6; color: white;' : ''}
                ${type === 'warning' ? 'background: #f59e0b; color: white;' : ''}
            `;

    document.body.appendChild(notification);

    // 3秒后自动移除
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * 触发图片上传
 */
function triggerImageUpload() {
    console.log('📷 triggerImageUpload called');
    const uploadInput = document.getElementById('imageUpload');
    console.log('🔍 Upload input element:', uploadInput);
    if (uploadInput) {
        uploadInput.click();
        console.log('✅ Click triggered');
    } else {
        console.error('❌ imageUpload element not found!');
    }
}

/**
 * 处理图片上传
 */
async function handleImageUpload(event) {
    console.log('🔍 handleImageUpload called', event);
    const file = event.target.files[0];
    console.log('📁 Selected file:', file);
    if (!file) {
        console.log('❌ No file selected');
        return;
    }

    // 验证文件类型
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    console.log('🔍 File type:', file.type);
    if (!validTypes.includes(file.type)) {
        console.log('❌ Invalid file type:', file.type);
        showNotification('❌ 不支持的图片格式', 'error');
        return;
    }

    // 验证文件大小 (20MB)
    console.log('📊 File size:', file.size, 'bytes');
    if (file.size > 20 * 1024 * 1024) {
        console.log('❌ File too large:', file.size);
        showNotification('❌ 文件过大（最大20MB）', 'error');
        return;
    }

    // 显示上传中状态
    console.log('📤 Starting upload...');
    showNotification('📤 正在上传图片...', 'info');

    try {
        // 创建FormData
        const formData = new FormData();
        formData.append('file', file);
        console.log('📦 FormData created');

        // 上传图片 - 使用 AbortController 设置超时
        console.log('🚀 Sending request to /api/vision/upload');
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60秒超时

        try {
            const response = await fetch('/api/vision/upload', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            console.log('📡 Response status:', response.status);

            // 检查 HTTP 状态码
            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ HTTP Error:', response.status, errorText);
                throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
            }

            const result = await response.json();
            console.log('📋 Response data:', result);

            if (result.success) {
                uploadedImagePath = result.file_path;
                console.log('✅ Upload successful, path:', uploadedImagePath);
                showNotification('✅ 图片上传成功', 'success');

                // 显示图片预览
                console.log('🖼️ Showing image preview');
                showImagePreview(file, result.file_path);
            } else {
                console.log('❌ Upload failed:', result.error);
                showNotification(`❌ 上传失败: ${result.error}`, 'error');
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            throw fetchError;
        }
    } catch (error) {
        console.error('💥 Upload error:', error);
        console.error('💥 Error name:', error.name);
        console.error('💥 Error message:', error.message);

        // 提供更详细的错误信息
        let errorMsg = '网络错误';
        if (error.name === 'AbortError') {
            errorMsg = '上传超时（请检查网络连接）';
        } else if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            errorMsg = '无法连接服务器（可能是CORS或网络问题）';
        } else if (error.message) {
            errorMsg = error.message;
        }
        showNotification(`❌ 上传失败: ${errorMsg}`, 'error');
    }
}

/**
 * 显示图片预览
 */
function showImagePreview(file, filePath) {
    console.log('🖼️ showImagePreview called', { file: file.name, filePath });
    const reader = new FileReader();
    reader.onload = (e) => {
        console.log('📖 FileReader loaded');
        // 创建预览容器
        const previewHtml = `
                    <div class="image-preview" id="imagePreview">
                        <div class="image-preview-header">
                            <span>📷 已上传图片</span>
                            <button onclick="removeImagePreview()" class="remove-btn">✕</button>
                        </div>
                        <img src="${e.target.result}" alt="预览图" style="max-width: 200px; max-height: 200px; border-radius: 8px;">
                        <div class="image-preview-actions">
                            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
                                💡 输入问题后点击发送，或直接发送识别图片内容
                            </div>
                        </div>
                    </div>
                `;

        // 插入到输入框上方
        const inputContainer = document.querySelector('.input-container');
        console.log('🔍 Input container:', inputContainer);
        const existing = document.getElementById('imagePreview');
        if (existing) {
            console.log('🗑️ Removing existing preview');
            existing.remove();
        }
        inputContainer.insertAdjacentHTML('beforebegin', previewHtml);
        console.log('✅ Preview inserted');
    };
    reader.onerror = (error) => {
        console.error('❌ FileReader error:', error);
    };
    console.log('📖 Starting FileReader...');
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
 * 在输入框中显示已存在的图片预览（用于编辑消息）
 */
function showImagePreviewInInput(imagePath) {
    console.log('🖼️ showImagePreviewInInput called', { imagePath });

    // 创建预览容器
    const previewHtml = `
                <div class="image-preview" id="imagePreview">
                    <div class="image-preview-header">
                        <span>📷 原消息图片</span>
                        <button onclick="removeImagePreview()" class="remove-btn">✕</button>
                    </div>
                    <img src="/${imagePath}" alt="预览图" style="max-width: 200px; max-height: 200px; border-radius: 8px;">
                    <div class="image-preview-actions">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
                            💡 编辑消息时保留原图片
                        </div>
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

    // 设置上传的图片路径，以便发送时使用
    uploadedImagePath = imagePath;
    console.log('✅ Preview inserted for editing');
}

/**
 * 打开图片查看器
 */
function openImageViewer(imageSrc) {
    const modal = document.getElementById('imageViewerModal');
    const img = document.getElementById('imageViewerImg');
    img.src = imageSrc;
    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // 防止背景滚动
}

/**
 * 关闭图片查看器
 */
function closeImageViewer(event) {
    // 只在点击背景或关闭按钮时关闭
    if (event.target.id === 'imageViewerModal' || event.target.classList.contains('image-viewer-close')) {
        const modal = document.getElementById('imageViewerModal');
        modal.classList.remove('active');
        document.body.style.overflow = ''; // 恢复背景滚动
    }
}

// 按ESC键关闭图片查看器
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('imageViewerModal');
        if (modal.classList.contains('active')) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
});

/**
 * 切换侧边栏折叠状态
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const icon = document.getElementById('sidebarToggleIcon');
    const isMobile = window.innerWidth <= 768;

    if (isMobile) {
        // 移动端：显示/隐藏侧边栏
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('active');
    } else {
        // 桌面端：折叠/展开侧边栏
        sidebar.classList.toggle('collapsed');
        if (icon) {
            icon.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
        }
    }
}

/**
 * 分析上传的图片
 */
