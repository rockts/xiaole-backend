-- 数据库性能优化 - v0.6.2
-- 额外的索引优化和查询性能改进

-- 使用DO块来检查并创建索引（兼容旧版PostgreSQL）

-- 1. sessions表索引（如果表存在）
DO $$
BEGIN
    -- 检查表是否存在
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sessions') THEN
        -- 检查并创建索引
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_sessions_user_id') THEN
            CREATE INDEX idx_sessions_user_id ON sessions(user_id);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_sessions_created_at') THEN
            CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_sessions_updated_at') THEN
            CREATE INDEX idx_sessions_updated_at ON sessions(updated_at DESC);
        END IF;
    END IF;
END $$;

-- 2. memories表复合索引优化
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_memories_user_time') THEN
        CREATE INDEX idx_memories_user_time ON memories(user_id, created_at DESC);
    END IF;
END $$;

-- 3. messages表role索引
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_messages_role') THEN
        CREATE INDEX idx_messages_role ON messages(role);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_messages_session_role') THEN
        CREATE INDEX idx_messages_session_role ON messages(session_id, role, created_at DESC);
    END IF;
END $$;

-- 4. proactive_questions会话索引
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_proactive_session_id') THEN
        CREATE INDEX idx_proactive_session_id ON proactive_questions(session_id);
    END IF;
END $$;

-- 5. 课程表相关索引（schedules表，如果存在）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'schedules') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_schedules_user_id') THEN
            CREATE INDEX idx_schedules_user_id ON schedules(user_id);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_schedules_day_of_week') THEN
            CREATE INDEX idx_schedules_day_of_week ON schedules(day_of_week);
        END IF;
    END IF;
END $$;

-- 6. 添加VACUUM分析（定期维护）
-- 这会更新统计信息，帮助查询规划器做出更好的决策
VACUUM ANALYZE messages;
VACUUM ANALYZE memories;
VACUUM ANALYZE sessions;
VACUUM ANALYZE proactive_questions;

-- 7. 查看表大小和索引使用情况
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 8. 验证所有索引
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
