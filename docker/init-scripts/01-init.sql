-- =============================================================================
-- MasterBuilder7 - PostgreSQL Initialization
-- =============================================================================

-- Create additional databases for different environments
CREATE DATABASE masterbuilder7_test;

-- Create application user (if not using postgres)
-- CREATE USER mb7_app WITH PASSWORD 'change_me_in_production';
-- GRANT ALL PRIVILEGES ON DATABASE masterbuilder7 TO mb7_app;
-- GRANT ALL PRIVILEGES ON DATABASE masterbuilder7_test TO mb7_app;

-- Enable required extensions
\c masterbuilder7;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schema
CREATE SCHEMA IF NOT EXISTS mb7;

-- Set search path
ALTER DATABASE masterbuilder7 SET search_path TO mb7, public;

-- Grant schema permissions
-- GRANT USAGE ON SCHEMA mb7 TO mb7_app;
-- GRANT CREATE ON SCHEMA mb7 TO mb7_app;
