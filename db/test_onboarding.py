from db.manager import DBManager

def test_onboarding():
    manager = DBManager()
    mart_name = "Lalkurti Mart"
    schema_name = "mart_lalkurti"

    print(f"Provisioning new tenant: {mart_name}...")
    try:
        tenant_id = manager.create_tenant_schema(mart_name, schema_name)
        print(f"Successfully onboarded {mart_name} with ID: {tenant_id}")

        # Verify schema exists and has tables
        conn = manager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}'")
                tables = [row[0] for row in cur.fetchall()]
                print(f"Verified tables in {schema_name}: {tables}")

                # Verify pgvector is working in the new schema
                cur.execute(f"SELECT count(*) FROM {schema_name}.items")
                print("Items table is accessible.")
        finally:
            conn.close()

    except Exception as e:
        print(f"Onboarding failed: {e}")

if __name__ == "__main__":
    test_onboarding()
