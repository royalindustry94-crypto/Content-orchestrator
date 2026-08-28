-- LOCAL / CI ONLY.
-- Provides the minimal Supabase-auth surface and runtime login required by
-- Content Orchestrator tests and local Docker Postgres. Never apply this file
-- to a managed Supabase project.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
        CREATE ROLE app_runtime LOGIN PASSWORD 'app_runtime' NOBYPASSRLS NOCREATEROLE NOCREATEDB;
    ELSE
        ALTER ROLE app_runtime LOGIN PASSWORD 'app_runtime' NOBYPASSRLS NOCREATEROLE NOCREATEDB;
    END IF;
END
$$;
