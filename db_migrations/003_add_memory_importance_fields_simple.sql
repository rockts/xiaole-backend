-- v0.6.0 Phase 3: 为 memories 表添加重要性评分相关字段 (简化版)
-- 此版本直接添加字段,不使用DO块,不检查字段是否存在
-- 如果字段已存在会报错,但可以忽略

-- 添加重要性评分字段 (0.0-1.0)
ALTER TABLE memories ADD COLUMN importance_score REAL DEFAULT 0.0;

-- 添加访问次数字段
ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0;

-- 添加最后访问时间字段
ALTER TABLE memories ADD COLUMN last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 添加归档状态字段
ALTER TABLE memories ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;

-- 创建索引
CREATE INDEX idx_memories_importance_score ON memories(importance_score DESC);
CREATE INDEX idx_memories_is_archived ON memories(is_archived);

-- 为现有记忆设置初始值
UPDATE memories SET importance_score = 0.5 WHERE importance_score IS NULL;
UPDATE memories SET last_accessed_at = created_at WHERE last_accessed_at IS NULL;
