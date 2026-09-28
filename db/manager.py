import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import re

load_dotenv()

class DBManager:
    def __init__(self, read_only: bool = False):
        self.db_user = os.getenv(
            "CONTEXT_SERVICE_DB_USER" if read_only else "POSTGRES_USER",
            os.getenv("POSTGRES_USER"),
        )
        self.db_password = os.getenv(
            "CONTEXT_SERVICE_DB_PASSWORD" if read_only else "POSTGRES_PASSWORD",
            os.getenv("POSTGRES_PASSWORD"),
        )
        self.db_name = os.getenv("POSTGRES_DB")
        self.db_host = os.getenv("POSTGRES_HOST")
        self.db_port = os.getenv("POSTGRES_PORT", "5432")

    def get_connection(self):
        return psycopg2.connect(
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port
        )

    def get_read_only_connection(self):
        return DBManager(read_only=True).get_connection()

    def get_migration_files(self, directory):
        if not os.path.exists(directory):
            return []
        files = [f for f in os.listdir(directory) if f.endswith(".sql")]
        files.sort()
        return files

    def extract_version(self, filename):
        match = re.match(r"(\d+)_", filename)
        if match:
            return int(match.group(1))
        return None

    def apply_migrations(self, conn, directory, schema_name=None):
        if schema_name:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name)))

        files = self.get_migration_files(directory)

        # Use explicit schema for migration_history to avoid ambiguity
        history_table = sql.Identifier('migration_history')
        if schema_name:
            history_table = sql.SQL('{}.{}').format(sql.Identifier(schema_name), sql.Identifier('migration_history'))

        with conn.cursor() as cur:
            cur.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT NOW(),
                    filename TEXT NOT NULL
                );
            """).format(history_table))

            cur.execute(sql.SQL("SELECT version FROM {}").format(history_table))
            applied_versions = [row[0] for row in cur.fetchall()]

        for filename in files:
            version = self.extract_version(filename)
            if version is None:
                continue

            if version not in applied_versions:
                print(f"Applying {filename} to schema {schema_name or 'public'}...")
                with open(os.path.join(directory, filename), "r") as f:
                    sql_content = f.read()

                try:
                    with conn.cursor() as cur:
                        cur.execute(sql_content)
                        cur.execute(
                            sql.SQL("INSERT INTO {} (version, filename) VALUES (%s, %s)").format(history_table),
                            (version, filename)
                        )
                    print(f"Successfully applied {filename}")
                except Exception as e:
                    print(f"Error applying {filename}: {e}")
                    raise e

    def create_tenant_schema(self, mart_name, schema_name):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    # 1. Register tenant in global table
                    cur.execute(
                        "INSERT INTO tenants (mart_name, schema_name, status) VALUES (%s, %s, %s) RETURNING tenant_id",
                        (mart_name, schema_name, 'onboarding')
                    )
                    tenant_id = cur.fetchone()[0]

                    # 2. Create the schema
                    cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))

            # 3. Apply migrations to the new schema
            # We use a separate connection or transaction block for migrations to avoid
            # locking the whole session if one migration fails
            self.apply_migrations(conn, "db/migrations/tenant", schema_name)

            return tenant_id
        finally:
            conn.close()
