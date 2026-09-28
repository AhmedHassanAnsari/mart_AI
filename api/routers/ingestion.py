from fastapi import APIRouter, HTTPException, Depends, status
from db.manager import DBManager
from api.schemas import TenantCreate, TenantResponse, CheckoutRequest, CheckoutResponse
from api.routers.auth import get_current_user
from uuid import uuid4
from psycopg2 import sql
import json
from datetime import datetime

router = APIRouter(prefix="/ingestion", tags=["Ingestion API"])
db_manager = DBManager()

@router.post("/tenants", response_model=TenantResponse)
async def onboard_tenant(tenant_data: TenantCreate):
    # Generate a clean schema name from mart_name
    schema_name = f"mart_{tenant_data.mart_name.lower().replace(' ', '_')}"

    try:
        # We modify the DBManager logic slightly to support full tenant details
        # Since we can't easily change DBManager without breaking others,
        # we'll implement the detailed onboarding here or update DBManager.
        # Let's update DBManager later, for now we do it here to be precise with the schema.

        conn = db_manager.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    # 1. Register tenant in global table
                    cur.execute(
                        "INSERT INTO tenants (mart_name, schema_name, address, operating_hours, owner_name, contact_info, status) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING tenant_id",
                        (
                            tenant_data.mart_name,
                            schema_name,
                            tenant_data.address,
                            json.dumps(tenant_data.operating_hours),
                            tenant_data.owner_name,
                            tenant_data.contact_info,
                            'onboarding'
                        )
                    )
                    tenant_id = cur.fetchone()[0]

                    # 2. Create the schema
                    cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))

            # 3. Apply migrations
            db_manager.apply_migrations(conn, "migrations/tenant", schema_name)

            return TenantResponse(
                tenant_id=tenant_id,
                schema_name=schema_name,
                status="onboarding"
            )
        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")

@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    request: CheckoutRequest,
    current_user_id: str = Depends(get_current_user)
):
    conn = db_manager.get_connection()
    try:
        # 1. Resolve tenant schema
        with conn.cursor() as cur:
            cur.execute("SELECT schema_name FROM tenants WHERE tenant_id = %s", (str(request.tenant_id),))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Tenant not found")
            schema_name = result[0]

            # Set search path for the transaction
            cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name)))

        # 2. Start transaction for the bill
        with conn:
            with conn.cursor() as cur:
                # Create Bill
                bill_id = uuid4()
                total_price = 0.0

                # We need to calculate the total price and handle items
                # Since we need cost_price_snapshot, we fetch it from items table
                bill_items_data = []

                for item in request.items:
                    # Fetch cost price
                    cur.execute("SELECT cost_price FROM items WHERE item_id = %s", (str(item.item_id),))
                    item_res = cur.fetchone()
                    if not item_res:
                        raise HTTPException(status_code=404, detail=f"Item {item.item_id} not found in tenant schema")

                    cost_price = item_res[0]
                    line_total = item.quantity * item.sale_price
                    total_price += line_total

                    bill_items_data.append({
                        "item_id": item.item_id,
                        "quantity": item.quantity,
                        "sale_price": item.sale_price,
                        "cost_price": cost_price
                    })

                # Create the bill header
                timestamp = request.timestamp or datetime.utcnow()
                cur.execute(
                    "INSERT INTO bills (bill_id, customer_id, timestamp, total_price) VALUES (%s, %s, %s, %s)",
                    (str(bill_id), str(current_user_id), timestamp, total_price)
                )

                # Create bill items and decrement inventory
                for b_item in bill_items_data:
                    cur.execute(
                        "INSERT INTO bill_items (bill_id, item_id, quantity, sale_price, cost_price_snapshot) VALUES (%s, %s, %s, %s, %s)",
                        (str(bill_id), str(b_item["item_id"]), b_item["quantity"], b_item["sale_price"], b_item["cost_price"])
                    )

                    # Decrement inventory
                    cur.execute(
                        "UPDATE inventory SET quantity_on_hand = quantity_on_hand - %s, last_updated = NOW() WHERE item_id = %s",
                        (b_item["quantity"], str(b_item["item_id"]))
                    )

                    # Verify stock didn't go negative (optional but good for integrity)
                    cur.execute("SELECT quantity_on_hand FROM inventory WHERE item_id = %s", (str(b_item["item_id"]),))
                    stock = cur.fetchone()[0]
                    if stock < 0:
                        # In a real app, we might allow negative stock or raise error.
                        # For now, we'll let it be, but it will trigger the reorder alert.
                        pass

                return CheckoutResponse(
                    bill_id=bill_id,
                    total_price=total_price,
                    status="success"
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")
    finally:
        conn.close()
