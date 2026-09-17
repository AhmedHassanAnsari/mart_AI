-- Global Inventory Triggers
-- 002_inventory_triggers.sql

CREATE OR REPLACE FUNCTION public.notify_inventory_reorder() RETURNS trigger AS $$
DECLARE
    reorder_val INTEGER;
    v_schema_name TEXT;
    v_tenant_id UUID;
BEGIN
    RAISE NOTICE 'Trigger function called for item %: OLD=%, NEW=%', NEW.item_id, OLD.quantity_on_hand, NEW.quantity_on_hand;

    -- 1. Get the reorder point from the items table in the current schema
    SELECT reorder_point INTO reorder_val
    FROM items
    WHERE item_id = NEW.item_id;

    RAISE NOTICE 'Reorder point for item % is %', NEW.item_id, reorder_val;

    -- 2. Check if it just crossed BELOW the reorder point
    IF (OLD.quantity_on_hand >= reorder_val AND NEW.quantity_on_hand < reorder_val) THEN
        -- Keep one global wake channel; tenant_id and schema_name identify the source.
        v_schema_name := current_schema();

        -- Get the tenant_id from the global tenants table
        SELECT tenant_id INTO v_tenant_id
        FROM public.tenants
        WHERE schema_name = v_schema_name;

        -- Notify on a GLOBAL channel: inventory_reorder_events
        PERFORM pg_notify(
            'inventory_reorder_events',
            json_build_object(
                'item_id', NEW.item_id,
                'quantity', NEW.quantity_on_hand,
                'reorder_point', reorder_val,
                'tenant_id', v_tenant_id,
                'schema_name', v_schema_name
            )::text
        );

        RAISE NOTICE 'Reorder notification sent for item % in schema %', NEW.item_id, v_schema_name;
    ELSE
        RAISE NOTICE 'Condition not met: OLD=%, NEW=%, reorder=%.', OLD.quantity_on_hand, NEW.quantity_on_hand, reorder_val;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
