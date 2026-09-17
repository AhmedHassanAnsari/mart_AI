import json

from fastapi.testclient import TestClient

from context_service import main


client = TestClient(main.app)


def test_only_context_tool_is_discoverable():
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "list", "method": "tools/list", "params": {}},
    )
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["get_reorder_context"]


def test_context_tool_merges_facts_and_live_policy(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_live_operational_facts",
        lambda tenant_id, item_id: {
            "tenant_id": tenant_id,
            "item": {"item_id": item_id, "name": "Cooler"},
            "inventory": {"quantity_on_hand": 4, "reorder_point": 5},
            "pending_orders": [],
            "sales_velocity": {"total_units_sold_last_14d": 2},
        },
    )
    monkeypatch.setattr(
        main,
        "get_live_ksor_policies",
        lambda tenant_id, item_id: {
            "reorder_policy": "live reorder policy",
            "agent_permissions": "live approval policy",
        },
    )

    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "call",
            "method": "tools/call",
            "params": {
                "name": "get_reorder_context",
                "arguments": {"tenant_id": "tenant-1", "item_id": "item-1"},
            },
        },
    )
    assert response.status_code == 200
    context = json.loads(response.json()["result"]["content"][0]["text"])
    assert context["inventory"]["quantity_on_hand"] == 4
    assert context["ksor_policy"]["reorder_policy"] == "live reorder policy"