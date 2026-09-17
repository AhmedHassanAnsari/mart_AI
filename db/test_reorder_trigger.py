import psycopg2
from psycopg2 import sql, extensions
from db.manager import DBManager
import json
import time
import threading

def apply_latest_migrations():
    manager = DBManager()
    conn = manager.get_connection()
    try:
        # 1. Apply global migrations
        manager.apply_migrations(conn, "db/migrations/global")
        # 2. Apply tenant migrations to the test mart
        manager.apply_migrations(conn, "db/migrations/tenant", "mart_lalkurti_electronics")
        conn.commit()
        print("Migrations applied successfully.")
    finally:
        conn.close()

def listen_for_notifications():
    manager = DBManager()
    conn = manager.get_connection()
    conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    channel = "inventory_reorder_events"
    cur.execute(sql.SQL("LISTEN {}").format(sql.Identifier(channel)))
    print(f"Listening on channel: {channel}...")

    # Wait for a notification
    start_time = time.time()
    while time.time() - start_time < 15:
        if conn.poll() == extensions.POLL_OK:
            notifies = conn.notifies
            if notifies:
                for notify in notifies:
                    print(f"NOTIFICATION RECEIVED: {notify.payload}")
                return True
        time.sleep(0.1)

    print("Timed out waiting for notification.")
    return False

def trigger_reorder():
    manager = DBManager()
    conn = manager.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SET search_path TO mart_lalkurti_electronics, public"))

                # Find Cooler item_id
                cur.execute("SELECT item_id FROM items WHERE name = 'Cooler'")
                item_id = cur.fetchone()[0]

                # RESET stock to 50 to ensure we cross the threshold
                print("Resetting Cooler stock to 50...")
                cur.execute("UPDATE inventory SET quantity_on_hand = 50 WHERE item_id = %s", (item_id,))

                # Now sell enough to cross reorder point (reorder point is 5)
                # Sell 46 -> resulting stock 4
                print("Selling 46 coolers to bring stock to 4 (Crosses reorder point 5)...")
                cur.execute(
                    "UPDATE inventory SET quantity_on_hand = quantity_on_hand - 46 WHERE item_id = %s",
                    (item_id,)
                )
    finally:
        conn.close()

if __name__ == "__main__":
    apply_latest_migrations()

    # Start listener in a thread
    result = {"notified": False}
    def worker():
        result["notified"] = listen_for_notifications()

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(2) # Give listener time to start
    trigger_reorder()
    t.join()

    if result["notified"]:
        print("\nSUCCESS: Reorder trigger fired and notification received!")
    else:
        print("\nFAILURE: Reorder trigger did not fire.")
        exit(1)
