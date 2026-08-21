// Theme and settings related functions extracted from app.js
const themeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
let systemThemeListener = null;
let themeInitialized = false;

export function initTheme() {
    if (themeInitialized) return;
    themeInitialized = true;

    const settings = getSettings();
    const preference = settings.themePreference || 'system';
    applyThemePreference(preference);

    // Add change event delegation for settings panel
    const settingsTab = document.getElementById('settings');
    if (settingsTab) {
        settingsTab.addEventListener('change', (e) => {
            const target = e.target;
            const action = target.getAttribute('data-setting-change');
            if (!action) return;

            switch (action) {
                case 'updateThemePreference':
                    updateThemePreference(target.value);
                    break;
                case 'toggleKeyboardShortcuts':
                    toggleKeyboardShortcuts(target.checked);
                    break;
                case 'toggleShortcutHints':
                    toggleShortcutHints(target.checked);
                    break;
                case 'updateResponseStyle':
                    updateResponseStyle(target.value);
                    break;
                case 'toggleProactiveQA':
                    toggleProactiveQA(target.checked);
                    break;
                default:
                    break;
            }
        });
    }
}

export function applyInitialSettings() {
    const settings = getSettings();

    const themeSelect = document.getElementById('themePreference');
    if (themeSelect) themeSelect.value = settings.themePreference;

    const keyboardToggle = document.getElementById('keyboardShortcuts');
    if (keyboardToggle) keyboardToggle.checked = settings.keyboardShortcuts;

    const shortcutToggle = document.getElementById('shortcutHintsEnabled');
    if (shortcutToggle) shortcutToggle.checked = settings.shortcutHintsEnabled;

    const responseStyle = document.getElementById('responseStyle');
    if (responseStyle) responseStyle.value = settings.responseStyle;

    const proactiveToggle = document.getElementById('proactiveQA');
    if (proactiveToggle) proactiveToggle.checked = settings.proactiveQA;

    if (settings.shortcutHintsEnabled) {
        showShortcutHints();
    }

    initVoiceSettings();
}

export function addSystemThemeListener(listener) {
    if (!listener) return;
    if (themeMediaQuery.addEventListener) {
        themeMediaQuery.addEventListener('change', listener);
    } else if (themeMediaQuery.addListener) {
        themeMediaQuery.addListener(listener);
    }
}

export function removeSystemThemeListener(listener) {
    if (!listener) return;
    if (themeMediaQuery.removeEventListener) {
        themeMediaQuery.removeEventListener('change', listener);
    } else if (themeMediaQuery.removeListener) {
        themeMediaQuery.removeListener(listener);
    }
}

export function setTheme(theme) {
    const html = document.documentElement;
    html.setAttribute('data-theme', theme);

    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
}

export function toggleTheme() {
    const settings = getSettings();
    const cycle = ['system', 'light', 'dark'];
    const currentPreference = settings.themePreference || 'system';
    const nextPreference = cycle[(cycle.indexOf(currentPreference) + 1) % cycle.length];

    settings.themePreference = nextPreference;
    saveSettings(settings);
    applyThemePreference(nextPreference);

    if (typeof showToast === 'function') {
        showToast(`✅ 主题偏好已切换为：${getThemeLabel(nextPreference)}`, 'success');
    }
}

export function applyThemePreference(preference) {
    const resolvedPreference = preference || 'system';

    removeSystemThemeListener(systemThemeListener);
    systemThemeListener = null;

    if (resolvedPreference === 'system') {
        const theme = themeMediaQuery.matches ? 'dark' : 'light';
        setTheme(theme);
        systemThemeListener = (event) => setTheme(event.matches ? 'dark' : 'light');
        addSystemThemeListener(systemThemeListener);
        localStorage.removeItem('theme');
    } else {
        setTheme(resolvedPreference);
        localStorage.setItem('theme', resolvedPreference);
    }
}

export function getThemeLabel(value) {
    const labels = {
        system: '跟随系统',
        light: '始终亮色',
        dark: '始终暗色'
    };
    return labels[value] || value;
}

const DEFAULT_SETTINGS = {
    themePreference: 'system',
    keyboardShortcuts: true,
    shortcutHintsEnabled: true,
    responseStyle: 'balanced',
    proactiveQA: true
};

export function getSettings() {
    const saved = localStorage.getItem('userSettings');
    return saved ? JSON.parse(saved) : { ...DEFAULT_SETTINGS };
}

export function saveSettings(settings) {
    localStorage.setItem('userSettings', JSON.stringify(settings));
}


export function updateThemePreference(value) {
    const settings = getSettings();
    settings.themePreference = value;
    saveSettings(settings);
    applyThemePreference(value);
    showToast(`✅ 主题偏好已设置为：${getThemeLabel(value)}`, 'success');
}

export function toggleKeyboardShortcuts(enabled) {
    const settings = getSettings();
    settings.keyboardShortcuts = enabled;
    saveSettings(settings);
    showToast(enabled ? '✅ 快捷键已启用' : '⚠️ 快捷键已禁用', enabled ? 'success' : 'warning');
}

export function toggleShortcutHints(enabled) {
    const settings = getSettings();
    settings.shortcutHintsEnabled = enabled;
    saveSettings(settings);

    const hints = document.getElementById('shortcutHints');
    if (enabled) {
        showShortcutHints();
    } else if (hints) {
        hints.style.opacity = '0';
        setTimeout(() => {
            hints.style.display = 'none';
        }, 300);
    }
    showToast(enabled ? '✅ 快捷键提示已显示' : '⚠️ 快捷键提示已隐藏', enabled ? 'success' : 'warning');
}

export function updateResponseStyle(style) {
    const settings = getSettings();
    settings.responseStyle = style;
    saveSettings(settings);

    const labels = {
        concise: '简洁模式',
        balanced: '平衡模式',
        detailed: '详细模式',
        professional: '专业模式'
    };
    showToast(`✅ AI响应风格已设置为：${labels[style]}`, 'success');
}

export function toggleProactiveQA(enabled) {
    const settings = getSettings();
    settings.proactiveQA = enabled;
    saveSettings(settings);
    showToast(enabled ? '✅ 主动问答提示已启用' : '⚠️ 主动问答提示已禁用', enabled ? 'success' : 'warning');
}

export function resetSettings() {
    if (confirm('确定要重置所有设置为默认值吗？')) {
        localStorage.removeItem('userSettings');
        localStorage.removeItem('theme');
        initSettings();
        applyThemePreference('system');
        showToast('✅ 所有设置已重置为默认值', 'success');
    }
}

// Placeholder functions expected to exist globally
function showToast(message, type) {
    if (window.showToast) {
        window.showToast(message, type);
    }
}

function showShortcutHints() {
    if (window.showShortcutHints) {
        window.showShortcutHints();
    }
}

function initVoiceSettings() {
    if (window.initVoiceSettings) {
        window.initVoiceSettings();
    }
}
