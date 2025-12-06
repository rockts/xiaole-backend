/**
 * v0.6.0 前端性能优化模块
 * 提供数据缓存、API并发控制、懒加载等功能
 */

// === 数据缓存系统 ===
const DataCache = {
    storage: {
        sessions: { data: null, timestamp: 0 },
        memory: { data: null, timestamp: 0 },
        analytics: { data: null, timestamp: 0 },
        tools: { data: null, timestamp: 0 },
        reminders: { data: null, timestamp: 0 }
    },

    ttl: 60000, // 1分钟缓存

    // 检查缓存是否有效
    isValid(key) {
        const cache = this.storage[key];
        if (!cache || !cache.data) return false;
        return (Date.now() - cache.timestamp) < this.ttl;
    },

    // 获取缓存
    get(key) {
        if (this.isValid(key)) {
            return this.storage[key].data;
        }
        return null;
    },

    // 更新缓存
    set(key, data) {
        this.storage[key] = {
            data: data,
            timestamp: Date.now()
        };
    },

    // 清除缓存
    clear(key = null) {
        if (key) {
            this.storage[key] = { data: null, timestamp: 0 };
        } else {
            // 清除所有缓存
            Object.keys(this.storage).forEach(k => {
                this.storage[k] = { data: null, timestamp: 0 };
            });
        }
    },

    // 获取缓存状态
    getStats() {
        const stats = {};
        Object.keys(this.storage).forEach(key => {
            const cache = this.storage[key];
            stats[key] = {
                hasData: !!cache.data,
                age: cache.timestamp ? Date.now() - cache.timestamp : null,
                valid: this.isValid(key)
            };
        });
        return stats;
    }
};

// === API并发控制 ===
const APIController = {
    activeRequests: 0,
    maxConcurrent: 3,
    requestQueue: [],

    // 等待有可用插槽
    async waitForSlot() {
        while (this.activeRequests >= this.maxConcurrent) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    },

    // 带并发控制的fetch
    async fetch(url, options = {}) {
        await this.waitForSlot();

        this.activeRequests++;
        try {
            return await fetch(url, options);
        } finally {
            this.activeRequests--;
        }
    },

    // 获取状态
    getStatus() {
        return {
            active: this.activeRequests,
            max: this.maxConcurrent,
            available: this.maxConcurrent - this.activeRequests
        };
    }
};

// === 防抖函数 ===
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// === 节流函数 ===
function throttle(func, limit) {
    let inThrottle;
    return function (...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// === 懒加载管理器 ===
const LazyLoader = {
    // 已加载的标签页
    loadedTabs: new Set(),

    // 标记标签页已加载
    markLoaded(tabName) {
        this.loadedTabs.add(tabName);
    },

    // 检查是否已加载
    isLoaded(tabName) {
        return this.loadedTabs.has(tabName);
    },

    // 重置加载状态
    reset(tabName = null) {
        if (tabName) {
            this.loadedTabs.delete(tabName);
        } else {
            this.loadedTabs.clear();
        }
    }
};

// === 性能监控 ===
const PerformanceMonitor = {
    metrics: {
        apiCalls: 0,
        cacheHits: 0,
        cacheMisses: 0,
        errors: 0
    },

    // 记录API调用
    recordAPICall() {
        this.metrics.apiCalls++;
    },

    // 记录缓存命中
    recordCacheHit() {
        this.metrics.cacheHits++;
    },

    // 记录缓存未命中
    recordCacheMiss() {
        this.metrics.cacheMisses++;
    },

    // 记录错误
    recordError() {
        this.metrics.errors++;
    },

    // 获取统计信息
    getStats() {
        const total = this.metrics.cacheHits + this.metrics.cacheMisses;
        return {
            ...this.metrics,
            cacheHitRate: total > 0 ? (this.metrics.cacheHits / total * 100).toFixed(1) + '%' : 'N/A'
        };
    },

    // 重置统计
    reset() {
        this.metrics = {
            apiCalls: 0,
            cacheHits: 0,
            cacheMisses: 0,
            errors: 0
        };
    }
};

// === 导出API ===
if (typeof window !== 'undefined') {
    window.DataCache = DataCache;
    window.APIController = APIController;
    window.LazyLoader = LazyLoader;
    window.PerformanceMonitor = PerformanceMonitor;
    window.debounce = debounce;
    window.throttle = throttle;

    // 调试工具
    window.debugPerformance = function () {
        console.log('=== 性能统计 ===');
        console.log('缓存状态:', DataCache.getStats());
        console.log('API控制:', APIController.getStatus());
        console.log('性能指标:', PerformanceMonitor.getStats());
    };
}
