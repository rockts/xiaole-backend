-- v0.6.0 Phase 3: 记忆系统升级字段

DO $$ 
BEGIN
    BEGIN
        ALTER TABLE memories ADD COLUMN importance_score FLOAT DEFAULT 0.5;
    EXCEPTION WHEN duplicate_column THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0;
    EXCEPTION WHEN duplicate_column THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE memories ADD COLUMN last_accessed_at TIMESTAMP DEFAULT NOW();
    EXCEPTION WHEN duplicate_column THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE memories ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
    EXCEPTION WHEN duplicate_column THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE memories ADD COLUMN summary TEXT;
    EXCEPTION WHEN duplicate_column THEN NULL;
    END;
END $$;

CREATE INDEX idx_memories_importance ON memories(importance_score DESC);
CREATE INDEX idx_memories_archived ON memories(is_archived);
