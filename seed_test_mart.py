from db.manager import DBManager
import psycopg2
from psycopg2 import sql
import json

def seed_test_mart():
    manager = DBManager()

    # Mart Details
    mart_name = "Lalkurti Electronics"
    schema_name = "mart_lalkurti_electronics"
    address = "Street 1, City A"
    operating_hours = {
        "default": "09:00-21:00",
        "overrides": {
            "Saturday": "10:00-20:00",
            "Sunday": "10:00-20:00"
        }
    }
    owner_name = "Ahmed"
    contact_info = "contact@mart.com"
    category_name = "Electronics"

    # Seed Items: (Name, Brand, Price, Reorder Point, Starting Inventory)
    seed_items = [
        ("TV", "LS", 40000.00, 10, 50),
        ("Cooler", "Asia", 30000.00, 5, 50),
    ]

    conn = manager.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Create the tenant and schema
                # We can't use manager.create_tenant_schema directly because we need to
                # insert custom details (address, owner, etc.) into the tenants table.

                # First, ensure the schema is clean for this test
                cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name)))

                # Register tenant in global table
                cur.execute(
                    "INSERT INTO tenants (mart_name, schema_name, address, operating_hours, owner_name, contact_info, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING tenant_id",
                    (mart_name, schema_name, address, json.dumps(operating_hours), owner_name, contact_info, 'active')
                )
                tenant_id = cur.fetchone()[0]
                print(f"Registered tenant {mart_name} with ID: {tenant_id}")

                # Create the isolated schema
                cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
                print(f"Created schema: {schema_name}")

                # 2. Provision the schema using the migration runner
                # We call the manager's migration logic
                manager.apply_migrations(conn, "migrations/tenant", schema_name)
                print("Applied tenant migrations.")

                # 3. Handle Categories
                cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING category_id", (category_name,))
                category_id = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO tenant_categories (tenant_id, category_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (tenant_id, category_id)
                )
                print(f"Linked mart to category: {category_name}")

                # 4. Seed Items and Inventory
                # Set search path to the tenant schema
                cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name)))

                for name, brand, price, reorder, stock in seed_items:
                    # Insert Item
                    cur.execute(
                        "INSERT INTO items (name, brand, price, reorder_point) VALUES (%s, %s, %s, %s) RETURNING item_id",
                        (name, brand, price, reorder)
                    )
                    item_id = cur.fetchone()[0]

                    # Insert Inventory
                    cur.execute(
                        "INSERT INTO inventory (item_id, quantity_on_hand) VALUES (%s, %s)",
                        (item_id, stock)
                    )
                    print(f"Seeded item: {name} ({brand}) - Price: {price}, Stock: {stock}")

        print("\n--- Seed completed successfully! ---")

    except Exception as e:
        print(f"Seeding failed: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    seed_test_mart()
