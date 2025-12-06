-- v0.8.1 Add image_path to messages table
-- Purpose: Store image paths for messages with images

-- Add image_path column to messages table (use DO block for conditional add)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' 
        AND column_name = 'image_path'
    ) THEN
        ALTER TABLE messages ADD COLUMN image_path VARCHAR(500);
    END IF;
END $$;

-- Create index for faster image message queries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_messages_image_path'
    ) THEN
        CREATE INDEX idx_messages_image_path 
        ON messages(image_path) 
        WHERE image_path IS NOT NULL;
    END IF;
END $$;

-- Add comment
COMMENT ON COLUMN messages.image_path IS 'Path to uploaded image file (relative to uploads directory)';
