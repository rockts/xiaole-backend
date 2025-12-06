DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_behaviors' AND column_name='sentiment_score') THEN
        ALTER TABLE user_behaviors ADD COLUMN sentiment_score FLOAT DEFAULT 0.0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_behaviors' AND column_name='interaction_type') THEN
        ALTER TABLE user_behaviors ADD COLUMN interaction_type VARCHAR(50) DEFAULT 'chat';
    END IF;
END
$$;
