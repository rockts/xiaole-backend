-- 数据库性能优化 - v0.6.0
-- 为常用查询添加索引

-- 1. messages表索引优化
-- 常用查询: session_id过滤、按时间排序
CREATE INDEX IF NOT EXISTS idx_messages_session_id 
    ON messages(session_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at 
    ON messages(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_session_time 
    ON messages(session_id, created_at DESC);

-- 2. proactive_questions表索引优化
-- 常用查询: user_id + followup_asked, session_id, 时间范围
CREATE INDEX IF NOT EXISTS idx_proactive_user_asked 
    ON proactive_questions(user_id, followup_asked);

CREATE INDEX IF NOT EXISTS idx_proactive_created_at 
    ON proactive_questions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_proactive_original_question 
    ON proactive_questions(original_question);

CREATE INDEX IF NOT EXISTS idx_proactive_user_time 
    ON proactive_questions(user_id, created_at DESC);

-- 3. memories表索引优化
-- 常用查询: tag过滤、时间排序
CREATE INDEX IF NOT EXISTS idx_memories_tag 
    ON memories(tag);

CREATE INDEX IF NOT EXISTS idx_memories_timestamp 
    ON memories(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_memories_tag_time 
    ON memories(tag, timestamp DESC);

-- 4. user_behaviors表索引优化
-- 常用查询: user_id + 时间范围
CREATE INDEX IF NOT EXISTS idx_behaviors_user_time 
    ON user_behaviors(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_behaviors_timestamp 
    ON user_behaviors(timestamp DESC);

-- 5. tool_executions表索引优化
-- 常用查询: session_id、tool_name、时间
CREATE INDEX IF NOT EXISTS idx_tool_exec_session 
    ON tool_executions(session_id);

CREATE INDEX IF NOT EXISTS idx_tool_exec_tool_name 
    ON tool_executions(tool_name);

CREATE INDEX IF NOT EXISTS idx_tool_exec_timestamp 
    ON tool_executions(timestamp DESC);

-- 6. reminders表索引优化（如果存在）
CREATE INDEX IF NOT EXISTS idx_reminders_user_id 
    ON reminders(user_id);

CREATE INDEX IF NOT EXISTS idx_reminders_trigger_time 
    ON reminders(trigger_time);

CREATE INDEX IF NOT EXISTS idx_reminders_status 
    ON reminders(status);

CREATE INDEX IF NOT EXISTS idx_reminders_user_status 
    ON reminders(user_id, status);

-- 验证索引创建
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
