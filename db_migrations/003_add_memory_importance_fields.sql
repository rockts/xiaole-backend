-- v0.6.0 Phase 3: 为 memories 表添加重要性评分相关字段
-- 创建时间: 2025-01-11
-- 描述: 添加重要性评分、访问计数、最后访问时间、归档状态等字段

-- 添加字段（使用DO块实现IF NOT EXISTS效果）
DO $$
BEGIN
    -- 添加重要性评分字段 (0.0-1.0)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='memories' AND column_name='importance_score') THEN
        ALTER TABLE memories ADD COLUMN importance_score REAL DEFAULT 0.0;
    END IF;

    -- 添加访问次数字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='memories' AND column_name='access_count') THEN
        ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0;
    END IF;

    -- 添加最后访问时间字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='memories' AND column_name='last_accessed_at') THEN
        ALTER TABLE memories ADD COLUMN last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- 添加归档状态字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='memories' AND column_name='is_archived') THEN
        ALTER TABLE memories ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- 创建索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_memories_importance_score ON memories(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_is_archived ON memories(is_archived);

-- 为现有记忆设置初始重要性评分 (默认0.5表示中等重要性)
UPDATE memories SET importance_score = 0.5 WHERE importance_score IS NULL;

-- 更新所有记忆的最后访问时间为创建时间
UPDATE memories SET last_accessed_at = created_at WHERE last_accessed_at IS NULL;

-- 添加字段注释
COMMENT ON COLUMN memories.importance_score IS '记忆重要性评分(0.0-1.0),基于访问频率、内容相关性、时间衰减等因素综合计算';
COMMENT ON COLUMN memories.access_count IS '记忆被访问的次数统计';
COMMENT ON COLUMN memories.last_accessed_at IS '记忆最后一次被访问的时间';
COMMENT ON COLUMN memories.is_archived IS '是否已归档(低重要性记忆会被自动归档)';
