-- v0.8.1 User Feedback System
-- Store user ratings for AI responses to improve model

CREATE TABLE IF NOT EXISTS message_feedback (
    feedback_id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    user_id VARCHAR(255) DEFAULT 'default_user',
    message_content TEXT NOT NULL,
    feedback_type VARCHAR(10) NOT NULL CHECK (feedback_type IN ('good', 'bad')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes (skip if already exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_feedback_session'
    ) THEN
        CREATE INDEX idx_feedback_session ON message_feedback(session_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_feedback_type'
    ) THEN
        CREATE INDEX idx_feedback_type ON message_feedback(feedback_type);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_feedback_created'
    ) THEN
        CREATE INDEX idx_feedback_created ON message_feedback(created_at);
    END IF;
END
$$;
