-- Global Schema Migrations

-- 001_initial_setup.sql
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schema_name TEXT UNIQUE NOT NULL,
    mart_name TEXT NOT NULL,
    address TEXT,
    operating_hours JSONB,
    owner_name TEXT,
    contact_info TEXT,
    status TEXT CHECK (status IN ('onboarding', 'active', 'suspended')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS tenant_categories (
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(category_id) ON DELETE CASCADE,
    PRIMARY KEY (tenant_id, category_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    profile_info JSONB
);

CREATE OR REPLACE FUNCTION validate_customer_id() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.customers WHERE customer_id = NEW.customer_id) THEN
        RAISE EXCEPTION 'Customer ID % does not exist in public.customers', NEW.customer_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Migration tracking table for global schema (Implementation detail for manage_db.py)
CREATE TABLE IF NOT EXISTS migration_history (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    filename TEXT NOT NULL
);
