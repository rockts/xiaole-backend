import {
    initTheme,
    applyInitialSettings,
    toggleTheme,
    updateThemePreference,
    toggleKeyboardShortcuts,
    toggleShortcutHints,
    updateResponseStyle,
    toggleProactiveQA,
    toggleReminderNotifications,
    resetSettings
} from './modules/theme.js';
import {
    initNavigation,
    toggleSidebar,
    toggleSidebarCollapse,
    switchTab
} from './modules/navigation.js';
import {
    initComposer,
    sendMessageFromDiv,
    sendHomeMessage,
    triggerImageUpload,
    handleImageUpload,
    editMessage,
    clearEditingState,
    showImagePreviewInInput,
    removeImagePreview
} from './modules/composer.js';
import {
    initChatControls,
    newChat,
    openImageViewer,
    closeImageViewer
} from './modules/chat-controls.js';
import {
    initMemory,
    loadMemoryStats,
    loadRecentMemories,
    searchMemories,
    semanticSearch,
    editMemory,
    deleteMemory
} from './modules/memory.js';
import {
    initRemindersTasks,
    loadReminders,
    toggleExpiredReminders,
    showCreateReminderDialog,
    checkReminders,
    loadTasks,
    showCreateTaskDialog
} from './modules/reminders_tasks.js';
import {
    initDocuments,
    loadDocuments,
    handleDocumentUpload,
    viewDocumentSummary,
    exportDocumentSummary,
    deleteDocument
} from './modules/documents.js';
import {
    initSchedule,
    loadSchedule,
    saveSchedule,
    renderSchedule
} from './modules/schedule.js';
import {
    initTools,
    loadTools,
    loadToolHistory
} from './modules/tools.js';
import {
    initVoice,
    toggleListening,
    startListening,
    stopListening,
    startSpeaking,
    stopSpeaking,
    toggleConversationMode
} from './modules/voice.js';

// expose functions globally for existing inline handlers until HTML is refactored
window.toggleTheme = toggleTheme;
window.updateThemePreference = updateThemePreference;
window.toggleKeyboardShortcuts = toggleKeyboardShortcuts;
window.toggleShortcutHints = toggleShortcutHints;
window.updateResponseStyle = updateResponseStyle;
window.toggleProactiveQA = toggleProactiveQA;
window.toggleReminderNotifications = toggleReminderNotifications;
window.resetSettings = resetSettings;
window.toggleSidebar = toggleSidebar;
window.toggleSidebarCollapse = toggleSidebarCollapse;
window.switchTab = switchTab;
window.sendMessageFromDiv = sendMessageFromDiv;
window.sendHomeMessage = sendHomeMessage;
window.triggerImageUpload = triggerImageUpload;
window.handleImageUpload = handleImageUpload;
window.editMessage = editMessage;
window.clearEditingState = clearEditingState;
window.showImagePreviewInInput = showImagePreviewInInput;
window.removeImagePreview = removeImagePreview;
window.newChat = newChat;
window.openImageViewer = openImageViewer;
window.closeImageViewer = closeImageViewer;
window.loadMemoryStats = loadMemoryStats;
window.loadRecentMemories = loadRecentMemories;
window.searchMemories = searchMemories;
window.semanticSearch = semanticSearch;
window.editMemory = editMemory;
window.deleteMemory = deleteMemory;
window.loadReminders = loadReminders;
window.toggleExpiredReminders = toggleExpiredReminders;
window.showCreateReminderDialog = showCreateReminderDialog;
window.checkReminders = checkReminders;
window.loadTasks = loadTasks;
window.showCreateTaskDialog = showCreateTaskDialog;
window.loadDocuments = loadDocuments;
window.handleDocumentUpload = handleDocumentUpload;
window.viewDocumentSummary = viewDocumentSummary;
window.exportDocumentSummary = exportDocumentSummary;
window.deleteDocument = deleteDocument;
window.loadSchedule = loadSchedule;
window.saveSchedule = saveSchedule;
window.renderSchedule = renderSchedule;
window.loadTools = loadTools;
window.loadToolHistory = loadToolHistory;
window.toggleListening = toggleListening;
window.startListening = startListening;
window.stopListening = stopListening;
window.startSpeaking = startSpeaking;
window.stopSpeaking = stopSpeaking;
window.toggleConversationMode = toggleConversationMode;

// Ensure initialization runs even when script is injected after DOMContentLoaded
let __appInitialized = false;
function initApp() {
    if (__appInitialized) return;
    __appInitialized = true;
    initTheme();
    applyInitialSettings();
    initNavigation();
    initComposer();
    initChatControls();
    initMemory();
    initRemindersTasks();
    initDocuments();
    initSchedule();
    initTools();
    initVoice();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp, { once: true });
} else {
    initApp();
}

// Future modules can register their own event delegates here as they are extracted.
