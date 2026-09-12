from db.manager import DBManager

def main():
    manager = DBManager()

    # Apply Global Migrations
    print("Applying global migrations...")
    conn = manager.get_connection()
    try:
        manager.apply_migrations(conn, "migrations/global")
    finally:
        conn.close()

    # Apply Tenant Migrations to all existing tenants
    print("Applying tenant migrations to existing tenants...")
    conn = manager.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT schema_name FROM tenants")
            tenants = [row[0] for row in cur.fetchall()]

        for schema in tenants:
            print(f"Migrating tenant schema: {schema}")
            manager.apply_migrations(conn, "migrations/tenant", schema)
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        main()
        print("All migrations applied successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        exit(1)
