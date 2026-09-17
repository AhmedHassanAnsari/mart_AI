import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Ensure mart_AI root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.inventory_agent import handle_wake_event
from agent.schemas import ReorderDecision

load_dotenv()

async def run_tests():
    tenant_id = "788aeac9-8539-4ad5-8fc7-356b4d1633da"
    item_id = "7fc0f7ca-d8d8-439c-8a74-fec47be17c8d"

    print("=================================================================")
    print("TEST 1: Live Call (MCP server not yet running -> Expects Failure)")
    print("=================================================================")
    try:
        decision_fail = await handle_wake_event(tenant_id, item_id)
        print(f"Decision received: {decision_fail}")
        assert decision_fail.escalate_to_owner is True, "Expected escalation due to unavailable context service"
        print("✓ Test 1 Passed: Handled unavailable MCP context gracefully with escalation.")
    except Exception as e:
        print(f"Test 1 encountered error: {e}")

    print("\n=================================================================")
    print("TEST 2: Mock Context - Within Blast Radius Autonomous Order")
    print("=================================================================")
    # 5 units sold in 14 days -> 2x = 10 units to order.
    # Cost = 10 * 2000 = Rs. 20,000 <= Rs. 30,000 (Autonomous limit)
    mock_within_limit = {
        "tenant_id": tenant_id,
        "item": {
            "item_id": item_id,
            "name": "Electric Kettle",
            "brand": "Philips",
            "category": "Electronics",
            "retail_price": 3000.0,
            "cost_price": 2000.0,
            "reorder_point": 5
        },
        "inventory": {
            "quantity_on_hand": 3,
            "last_updated": "2026-09-14T10:00:00Z"
        },
        "sales_velocity": {
            "daily_average_sales_14d": 0.357,
            "total_units_sold_last_14d": 5,
            "window_days": 14
        },
        "pending_orders": [],
        "ksor_policy": {
            "reorder_quantity_rule": "2x total unit sales from the last 14 days",
            "autonomous_order_limit": 30000.0,
            "mart_profit_tier": "standard",
            "trusted_suppliers": [
                {"supplier_id": "sup_alpha", "name": "Alpha Electronics", "deal_frequency": 42},
                {"supplier_id": "sup_beta", "name": "Beta Distributors", "deal_frequency": 12}
            ]
        }
    }

    decision_ok = await handle_wake_event(tenant_id, item_id, mock_context=mock_within_limit)
    print("Decision 2:")
    print(json.dumps(decision_ok.model_dump(), indent=2))
    assert decision_ok.decision == "order", f"Expected 'order', got {decision_ok.decision}"
    assert decision_ok.within_blast_radius is True, "Expected within_blast_radius to be True"
    assert decision_ok.escalate_to_owner is False, "Expected escalate_to_owner to be False"
    print("✓ Test 2 Passed: Autonomous reorder correctly decided within blast radius.")

    print("\n=================================================================")
    print("TEST 3: Mock Context - Exceeds Blast Radius (Escalation to Owner)")
    print("=================================================================")
    # 20 units sold in 14 days -> 2x = 40 units to order.
    # Cost = 40 * 2000 = Rs. 80,000 > Rs. 30,000 limit -> Must escalate!
    mock_exceeds_limit = {
        "tenant_id": tenant_id,
        "item": {
            "item_id": item_id,
            "name": "Electric Kettle",
            "brand": "Philips",
            "category": "Electronics",
            "retail_price": 3000.0,
            "cost_price": 2000.0,
            "reorder_point": 5
        },
        "inventory": {
            "quantity_on_hand": 2,
            "last_updated": "2026-09-14T10:00:00Z"
        },
        "sales_velocity": {
            "daily_average_sales_14d": 1.43,
            "total_units_sold_last_14d": 20,
            "window_days": 14
        },
        "pending_orders": [],
        "ksor_policy": {
            "reorder_quantity_rule": "2x total unit sales from the last 14 days",
            "autonomous_order_limit": 30000.0,
            "mart_profit_tier": "standard",
            "trusted_suppliers": [
                {"supplier_id": "sup_alpha", "name": "Alpha Electronics", "deal_frequency": 42}
            ]
        }
    }

    decision_escalate = await handle_wake_event(tenant_id, item_id, mock_context=mock_exceeds_limit)
    print("Decision 3:")
    print(json.dumps(decision_escalate.model_dump(), indent=2))
    assert decision_escalate.within_blast_radius is False, "Expected within_blast_radius to be False"
    assert decision_escalate.escalate_to_owner is True, "Expected escalate_to_owner to be True"
    print("✓ Test 3 Passed: Successfully escalated to Mart Owner when blast radius exceeded.")

if __name__ == "__main__":
    asyncio.run(run_tests())
