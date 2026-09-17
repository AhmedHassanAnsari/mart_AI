-- Tenant Schema Migrations

-- 001_initial_setup.sql
CREATE TABLE IF NOT EXISTS items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    brand TEXT,
    price DECIMAL(12, 2) NOT NULL,
    cost_price DECIMAL(12, 2) NOT NULL,
    reorder_point INTEGER DEFAULT 0,
    embedding vector(1536), -- Adjusted for OpenAI embeddings
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory (
    item_id UUID PRIMARY KEY REFERENCES items(item_id) ON DELETE CASCADE,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bills (
    bill_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL, -- Reference to shared customers table
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    total_price DECIMAL(12, 2) NOT NULL
);

CREATE TRIGGER trg_validate_customer
BEFORE INSERT OR UPDATE ON bills
FOR EACH ROW EXECUTE FUNCTION public.validate_customer_id();

CREATE TABLE IF NOT EXISTS bill_items (
    bill_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id UUID REFERENCES bills(bill_id) ON DELETE CASCADE,
    item_id UUID REFERENCES items(item_id),
    quantity INTEGER NOT NULL,
    sale_price DECIMAL(12, 2) NOT NULL,
    cost_price_snapshot DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID REFERENCES items(item_id),
    quantity INTEGER NOT NULL,
    status TEXT CHECK (status IN ('pending', 'confirmed', 'delivered')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_memory (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    entry_type TEXT CHECK (entry_type IN ('raw', 'rollup')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration tracking table for tenant schema
CREATE TABLE IF NOT EXISTS migration_history (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    filename TEXT NOT NULL
);
