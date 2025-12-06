-- 添加会话置顶字段
-- v0.8.1 会话管理功能增强

-- 检查并添加pinned字段
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='conversations' AND column_name='pinned'
    ) THEN
        ALTER TABLE conversations ADD COLUMN pinned BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- 创建索引以优化置顶会话的查询
DROP INDEX IF EXISTS idx_conversations_pinned;
CREATE INDEX idx_conversations_pinned ON conversations(user_id, pinned, updated_at);
