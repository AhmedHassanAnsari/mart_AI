-- Tenant Inventory Triggers
-- 002_inventory_triggers.sql

CREATE TRIGGER trg_check_reorder
AFTER UPDATE OF quantity_on_hand ON inventory
FOR EACH ROW
EXECUTE FUNCTION public.notify_inventory_reorder();
