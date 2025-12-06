-- 主动提醒系统数据库表
-- 创建时间: 2025-11-10
-- 版本: v0.5.0

-- 1. 提醒表
CREATE TABLE IF NOT EXISTS reminders (
    reminder_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    reminder_type VARCHAR(50) NOT NULL,  -- time, weather, behavior, habit
    trigger_condition TEXT NOT NULL,     -- 触发条件（JSON格式字符串）
    content TEXT NOT NULL,               -- 提醒内容
    title VARCHAR(200),                  -- 提醒标题
    priority INTEGER DEFAULT 3,          -- 优先级（1-5，1最高）
    repeat BOOLEAN DEFAULT false,        -- 是否重复
    repeat_interval INTEGER,             -- 重复间隔（秒）
    enabled BOOLEAN DEFAULT true,        -- 是否启用
    last_triggered TIMESTAMP,            -- 最后触发时间
    trigger_count INTEGER DEFAULT 0,     -- 触发次数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 提醒历史表
CREATE TABLE IF NOT EXISTS reminder_history (
    history_id SERIAL PRIMARY KEY,
    reminder_id INTEGER REFERENCES reminders(reminder_id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,               -- 提醒内容快照
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_response TEXT,                  -- 用户回应
    response_time TIMESTAMP              -- 回应时间
);

-- 3. 创建索引
CREATE INDEX idx_reminders_user_id ON reminders(user_id);
CREATE INDEX idx_reminders_type ON reminders(reminder_type);
CREATE INDEX idx_reminders_enabled ON reminders(enabled);
CREATE INDEX idx_reminders_last_triggered ON reminders(last_triggered);
CREATE INDEX idx_reminder_history_user_id ON reminder_history(user_id);
CREATE INDEX idx_reminder_history_triggered_at ON reminder_history(triggered_at);

-- 4. 添加注释
COMMENT ON TABLE reminders IS '主动提醒配置表';
COMMENT ON TABLE reminder_history IS '提醒触发历史记录表';
COMMENT ON COLUMN reminders.trigger_condition IS '触发条件JSON: 
    time类型: {"datetime": "2025-12-25 10:00:00"}
    weather类型: {"condition": "rain", "location": "天水"}
    behavior类型: {"inactive_hours": 24}
    habit类型: {"pattern": "morning_greeting", "time": "08:00"}';
COMMENT ON COLUMN reminders.repeat_interval IS '重复间隔（秒），例如: 86400=1天, 3600=1小时';

-- 5. 插入示例数据（可选，用于测试）
INSERT INTO reminders (user_id, reminder_type, trigger_condition, content, title, priority, repeat, repeat_interval)
VALUES 
    ('default_user', 'time', '{"datetime": "2025-11-11 08:00:00"}', '早上好！新的一天开始了，今天要加油哦！', '早安问候', 1, true, 86400),
    ('default_user', 'behavior', '{"inactive_hours": 24}', '好久不见！最近怎么样？', '长时间未聊天提醒', 2, true, 86400),
    ('default_user', 'weather', '{"condition": "rain", "location": "天水"}', '今天可能会下雨，记得带伞哦！', '下雨提醒', 2, false, NULL),
    ('default_user', 'habit', '{"pattern": "evening_summary", "time": "21:00"}', '晚上好，今天过得怎么样？需要我帮你记录什么吗？', '晚间总结提醒', 3, true, 86400)
ON CONFLICT DO NOTHING;

-- 完成
SELECT 'Reminders tables created successfully!' as status;
