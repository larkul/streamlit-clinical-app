-- 1. Initial Setup and Extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify extension is installed
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_extension
        WHERE extname = 'pg_trgm'
    ) THEN
        RAISE NOTICE 'pg_trgm extension is installed';
    ELSE
        RAISE EXCEPTION 'pg_trgm extension failed to install';
    END IF;
END
$$;
