-- v0.8.0 Phase 3: 长文本总结功能
-- 文档表：存储上传的文件信息和总结结果

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50),
    
    -- 文件信息
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL,  -- pdf/docx/txt/md
    file_size INT NOT NULL,  -- 字节
    file_path VARCHAR(500) NOT NULL,
    
    -- 内容和总结
    content TEXT,  -- 提取的原始文本
    content_length INT,  -- 字符数
    summary TEXT,  -- 总结结果
    summary_length INT,  -- 总结字符数
    key_points TEXT,  -- JSON数组：关键要点
    
    -- 元数据
    chunk_count INT,  -- 分块数量
    processing_time FLOAT,  -- 处理耗时（秒）
    status VARCHAR(20) DEFAULT 'pending',  -- pending/processing/completed/failed
    error_message TEXT,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 索引（PostgreSQL 9.x 兼容：先尝试删除再创建）
DO $$
BEGIN
    -- 删除可能存在的旧索引
    DROP INDEX IF EXISTS idx_documents_user_id;
    DROP INDEX IF EXISTS idx_documents_session_id;
    DROP INDEX IF EXISTS idx_documents_status;
    DROP INDEX IF EXISTS idx_documents_created_at;
EXCEPTION WHEN OTHERS THEN
    -- 忽略错误
END $$;

-- 创建新索引
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_session_id ON documents(session_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_documents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_documents_timestamp ON documents;
CREATE TRIGGER trigger_update_documents_timestamp
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_documents_updated_at();

-- 注释
COMMENT ON TABLE documents IS 'v0.8.0 文档上传和总结记录';
COMMENT ON COLUMN documents.content IS '提取的原始文本内容';
COMMENT ON COLUMN documents.summary IS 'AI生成的总结';
COMMENT ON COLUMN documents.key_points IS 'JSON格式的关键要点列表';
COMMENT ON COLUMN documents.chunk_count IS '大文本分块数量';
