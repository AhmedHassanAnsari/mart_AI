import os
import sys
import json

# Ensure mart_AI root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.tools import get_live_ksor_policies, call_ksor_mcp_tool

def test_ksor_connection():
    print("Testing live connection to KSOR MCP server at http://127.0.0.1:8080/mcp...")
    tenant_id = "788aeac9-8539-4ad5-8fc7-356b4d1633da"
    item_id = "7fc0f7ca-d8d8-439c-8a74-fec47be17c8d"
    try:
        policies = get_live_ksor_policies(tenant_id, item_id)
        print("\n--- [SUCCESS] Live KSOR Reorder Policy Fetched ---")
        print(policies["reorder_policy"][:300] + "...")
        print("\n--- [SUCCESS] Live KSOR Agent Permissions Fetched ---")
        print(policies["agent_permissions"][:300] + "...")
        print("\n✓ Live KSOR MCP integration is working properly!")
    except Exception as e:
        print(f"\n✗ Error calling KSOR MCP server: {e}")

if __name__ == "__main__":
    test_ksor_connection()
