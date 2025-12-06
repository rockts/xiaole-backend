-- v0.9.0 Phase 1: Create face_encodings table
CREATE TABLE IF NOT EXISTS face_encodings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) DEFAULT 'default_user',
    name VARCHAR(100) NOT NULL,
    encoding FLOAT[],
    image_path VARCHAR(500),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'ix_face_encodings_user_id' AND n.nspname = 'public') THEN
        CREATE INDEX ix_face_encodings_user_id ON face_encodings (user_id);
    END IF;
END$$;
