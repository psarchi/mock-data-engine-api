CREATE TABLE IF NOT EXISTS datasets (
    id VARCHAR(255) PRIMARY KEY,
    schema_name VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB,
    seed BIGINT,
    chaos_applied TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schema_name ON datasets(schema_name);
CREATE INDEX IF NOT EXISTS idx_created_at ON datasets(created_at);
CREATE INDEX IF NOT EXISTS idx_expires_at ON datasets(expires_at);

CREATE OR REPLACE FUNCTION cleanup_expired_datasets()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM datasets WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
