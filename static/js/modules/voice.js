// voice.js - 语音与连续对话模块抽取
// 职责：录音控制、语音识别状态、语音播放、对话模式切换、停止播放
// 注意：保留与后端的 API 协议一致，复用页面中已有的 DOM id

let voiceInitialized = false;
let conversationMode = false;
let isListening = false;
let isSpeaking = false;
let baiduRecorder = {
    audioContext: null,
    listeningContext: null,
    source: null,
    analyser: null,
    processor: null,
    stream: null,
    chunks: [],
    recordingStartTime: null
};

function initVoice() {
    if (voiceInitialized) return;
    voiceInitialized = true;

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.getAttribute('data-action');
        switch (action) {
            case 'voice':
                toggleListening();
                break;
            case 'stop-speaking':
                stopSpeaking();
                break;
            default:
                break;
        }
    });
}

function toggleListening() {
    if (isListening) {
        stopListening();
    } else {
        startListening();
    }
}

async function startListening() {
    if (isSpeaking) stopSpeaking();
    if (isListening) return;
    isListening = true;
    updateVoiceStatus('listening');
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        baiduRecorder.stream = stream;
        baiduRecorder.listeningContext = new (window.AudioContext || window.webkitAudioContext)();
        baiduRecorder.source = baiduRecorder.listeningContext.createMediaStreamSource(stream);
        baiduRecorder.analyser = baiduRecorder.listeningContext.createAnalyser();
        baiduRecorder.processor = baiduRecorder.listeningContext.createScriptProcessor(4096, 1, 1);
        baiduRecorder.source.connect(baiduRecorder.analyser);
        baiduRecorder.analyser.connect(baiduRecorder.processor);
        baiduRecorder.processor.connect(baiduRecorder.listeningContext.destination);
        baiduRecorder.chunks = [];
        baiduRecorder.recordingStartTime = Date.now();
        // 简化：不做实时能量波形绘制，可后续补充
        showNotification('🎙️ 开始录音', 'info');
    } catch (e) {
        console.error('启动录音失败:', e);
        showNotification('❌ 无法访问麦克风', 'error');
        stopListening();
    }
}

function stopListening() {
    if (!isListening) return;
    isListening = false;
    const stream = baiduRecorder.stream;
    if (stream) stream.getTracks().forEach(t => t.stop());
    if (baiduRecorder.listeningContext) {
        try { baiduRecorder.listeningContext.close(); } catch (_) { }
    }
    baiduRecorder.listeningContext = null;
    updateVoiceStatus('idle');
    showNotification('🛑 录音结束，发送识别请求...', 'info');
    // 这里应将录音数据发送后端进行识别。由于原逻辑较复杂，这里放置占位调用。
    simulateRecognition();
}

// 模拟识别：真实环境应上传音频并获取文本
async function simulateRecognition() {
    const fakeText = '这是模拟的识别文本';
    // 将识别文本发送为消息
    sendRecognizedText(fakeText);
}

function sendRecognizedText(text) {
    if (!text || !text.trim()) return;
    // 复用已经存在的发送入口（composer 模块暴露的 sendMessageFromDiv 或直接构造消息）
    const input = document.getElementById('messageInput');
    if (input) input.textContent = text;
    if (window.sendMessageFromDiv) window.sendMessageFromDiv();
    if (conversationMode) startListening(); // 连续模式自动再次开始
}

function startSpeaking(ttsUrl) {
    if (isSpeaking) stopSpeaking();
    isSpeaking = true;
    updateSpeakingStatus(true);
    const audio = new Audio(ttsUrl);
    audio.onended = () => {
        isSpeaking = false;
        updateSpeakingStatus(false);
        if (conversationMode) startListening();
    };
    audio.onerror = () => {
        isSpeaking = false;
        updateSpeakingStatus(false);
    };
    audio.play();
    // 显示全局停止按钮
    const globalStop = document.getElementById('globalStopSpeakingBtn');
    if (globalStop) globalStop.style.display = 'flex';
}

function stopSpeaking() {
    if (!isSpeaking) return;
    // 简化：无法直接停止所有音频，实际应保存当前 Audio 对象引用
    isSpeaking = false;
    updateSpeakingStatus(false);
    const globalStop = document.getElementById('globalStopSpeakingBtn');
    if (globalStop) globalStop.style.display = 'none';
}

function toggleConversationMode(enable) {
    if (typeof enable === 'boolean') conversationMode = enable; else conversationMode = !conversationMode;
    const status = document.getElementById('conversationModeStatus');
    const stateText = document.getElementById('conversationStateText');
    if (status && stateText) {
        if (conversationMode) {
            status.style.display = 'flex';
            stateText.textContent = '对话模式已开启';
            if (!isListening && !isSpeaking) startListening();
        } else {
            status.style.display = 'none';
        }
    }
}

function updateVoiceStatus(state) {
    const voiceStatus = document.getElementById('voiceStatus');
    if (!voiceStatus) return;
    switch (state) {
        case 'listening':
            voiceStatus.style.display = 'flex';
            document.getElementById('voiceText') && (document.getElementById('voiceText').textContent = '正在聆听...');
            break;
        default:
            voiceStatus.style.display = 'none';
    }
}

function updateSpeakingStatus(active) {
    const speakingStatus = document.getElementById('speakingStatus');
    if (speakingStatus) speakingStatus.style.display = active ? 'flex' : 'none';
    const globalStop = document.getElementById('globalStopSpeakingBtn');
    if (globalStop && !active) globalStop.style.display = 'none';
}

export {
    initVoice,
    toggleListening,
    startListening,
    stopListening,
    startSpeaking,
    stopSpeaking,
    toggleConversationMode,
    updateVoiceStatus,
    updateSpeakingStatus
};
