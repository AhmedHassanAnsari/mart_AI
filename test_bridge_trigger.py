from db.manager import DBManager
import json

def trigger_event():
    manager = DBManager()
    conn = manager.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Payload matching the trigger's JSON shape
                payload = {
                    "item_id": "7fc0f7ca-d8d8-439c-8a74-fec47be17c8d",
                    "quantity": 4,
                    "reorder_point": 5,
                    "tenant_id": "788aeac9-8539-4ad5-8fc7-356b4d1633da",
                    "schema_name": "mart_lalkurti_electronics"
                }
                payload_str = json.dumps(payload)
                # Correct syntax for NOTIFY with payload
                cur.execute(f"NOTIFY inventory_reorder_events, %s", (payload_str,))
                print(f"Successfully sent notification: {payload_str}")
    finally:
        conn.close()

if __name__ == "__main__":
    trigger_event()
