-- 多轮任务规划功能数据库表
-- 创建时间: 2025-11-12
-- 版本: v0.8.0

-- 任务主表
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', 
    -- 状态: pending(待处理), in_progress(进行中), waiting(等待), completed(已完成), failed(失败), cancelled(已取消)
    parent_id INT REFERENCES tasks(id) ON DELETE CASCADE,
    order_num INT DEFAULT 0,
    priority INT DEFAULT 0, -- 优先级: 0-正常, 1-高, 2-紧急
    result TEXT, -- 执行结果
    error_message TEXT, -- 错误信息
    retry_count INT DEFAULT 0, -- 重试次数
    max_retries INT DEFAULT 3, -- 最大重试次数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 任务步骤表（详细执行步骤）
CREATE TABLE IF NOT EXISTS task_steps (
    id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_num INT NOT NULL,
    description TEXT NOT NULL,
    action_type VARCHAR(50), -- 操作类型: tool_call, user_confirm, wait, etc.
    action_params TEXT, -- 操作参数（JSON格式字符串）
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(task_id, step_num)
);

-- 创建索引提升查询性能
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_session_id ON tasks(session_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_parent_id ON tasks(parent_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_task_steps_task_id ON task_steps(task_id);
CREATE INDEX idx_task_steps_status ON task_steps(status);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_tasks_updated_at();

