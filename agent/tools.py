import os
import json
import logging
import requests
from typing import Dict, Any
from datetime import datetime
from agents import function_tool
from db.manager import DBManager
from psycopg2 import sql
from observability import current_observation, inject_trace_headers, trace_metadata

logger = logging.getLogger("context-service")

KSOR_MCP_URL = os.getenv("KSOR_MCP_URL", "http://127.0.0.1:8080/mcp")
CONTEXT_SERVICE_MCP_URL = os.getenv("CONTEXT_SERVICE_MCP_URL", "http://127.0.0.1:8001/mcp")

def _parse_mcp_sse_or_json(response_text: str) -> Dict[str, Any]:
    """
    Parses MCP server response, handling both standard JSON and text/event-stream (SSE) formats.
    """
    # 1. Try parsing directly as JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # 2. Parse as text/event-stream (lines starting with 'data:')
    for line in response_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            try:
                return json.loads(data_str)
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Unable to parse MCP response content: {response_text[:400]}")

def call_ksor_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Makes a live JSON-RPC call to the KSOR MCP server at http://127.0.0.1:8080/mcp.
    Supports stream=True for text/event-stream (SSE) transport.
    """
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": f"ksor-{tool_name}-{int(datetime.utcnow().timestamp())}",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    tenant_id = arguments.get("query", "")
    with current_observation(
        name=f"ksor-{tool_name}",
        as_type="retriever",
        input={"tool": tool_name, "arguments": arguments},
        metadata={"source": KSOR_MCP_URL},
    ) as observation:
      try:
        with requests.post(KSOR_MCP_URL, headers=headers, json=payload, stream=True, timeout=10) as response:
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            data = None

            if "text/event-stream" in content_type:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data:"):
                            json_str = line_str[len("data:"):].strip()
                            try:
                                data = json.loads(json_str)
                                break
                            except json.JSONDecodeError:
                                continue
            else:
                data = response.json()

            if not data:
                raise ValueError("No data received from KSOR MCP server")

            if "error" in data:
                raise RuntimeError(f"KSOR MCP Error: {data['error']}")

            result = data.get("result", {})
            content_items = result.get("content", [])
            
            # Extract text content from result
            texts = [item.get("text", "") for item in content_items if item.get("type") == "text"]
            result_text = "\n\n".join(texts)
            if observation is not None:
                observation.update(output=result_text)
            return result_text

      except Exception as e:
        if observation is not None:
            observation.update(level="ERROR", status_message=str(e))
        logger.error(f"Failed to query KSOR MCP server at {KSOR_MCP_URL}: {e}")
        raise RuntimeError(f"Live KSOR MCP call to {KSOR_MCP_URL} failed: {e}")

def get_live_ksor_policies(tenant_id: str, item_id: str) -> Dict[str, str]:
    """Search KSOR live for the policies relevant to one tenant/item evaluation."""
    scope = f"tenant_id={tenant_id}, item_id={item_id}"
    reorder_policy_text = call_ksor_mcp_tool(
        "search",
        {
            "query": (
                f"{scope}: reorder quantity formula, reorder thresholds, "
                "pending orders, and supplier rules"
            ),
            "k": 10,
        },
    )
    agent_permissions_text = call_ksor_mcp_tool(
        "search",
        {
            "query": (
                f"{scope}: Inventory agent permission scope, autonomous "
                "order blast radius, monetary limit, and approval rules"
            ),
            "k": 10,
        },
    )
    return {
        "reorder_policy": reorder_policy_text,
        "agent_permissions": agent_permissions_text
    }

def get_live_operational_facts(tenant_id: str, item_id: str) -> Dict[str, Any]:
    """
    Queries the PostgreSQL database (mart_ai_db) for real-time facts:
    inventory level, item metadata, 14-day sales velocity, and pending orders.
    """
    with current_observation(
        name="postgres-operational-facts",
        as_type="retriever",
        tenant_id=tenant_id,
        item_id=item_id,
        input={"tenant_id": tenant_id, "item_id": item_id},
        metadata=trace_metadata(tenant_id, item_id, access_mode="read_only"),
    ) as observation:
        db_manager = DBManager()
        conn = db_manager.get_read_only_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                # 1. Resolve tenant schema name
                cur.execute("SELECT schema_name FROM public.tenants WHERE tenant_id = %s", (tenant_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Tenant '{tenant_id}' not found in public.tenants")
                schema_name = row[0]

                # 2. Fetch item details
                cur.execute(
                    sql.SQL("SELECT name, brand, price, cost_price, reorder_point FROM {}.items WHERE item_id = %s").format(
                        sql.Identifier(schema_name)
                    ),
                    (item_id,)
                )
                item_row = cur.fetchone()
                if not item_row:
                    raise ValueError(f"Item '{item_id}' not found in schema '{schema_name}'")
            
                item_name, brand, retail_price, cost_price, reorder_point = item_row

                # 3. Fetch inventory level
                cur.execute(
                    sql.SQL("SELECT quantity_on_hand, last_updated FROM {}.inventory WHERE item_id = %s").format(
                        sql.Identifier(schema_name)
                    ),
                    (item_id,)
                )
                inv_row = cur.fetchone()
                quantity_on_hand = inv_row[0] if inv_row else 0
                last_updated = inv_row[1].isoformat() if inv_row and inv_row[1] else None

                # 4. Fetch pending orders
                cur.execute(
                    sql.SQL("SELECT order_id, quantity, status, created_at FROM {}.orders WHERE item_id = %s AND status = 'pending'").format(
                        sql.Identifier(schema_name)
                    ),
                    (item_id,)
                )
                pending_orders = [
                {
                    "order_id": str(r[0]),
                    "quantity": r[1],
                    "status": r[2],
                    "created_at": r[3].isoformat() if r[3] else None
                }
                    for r in cur.fetchall()
                ]

                # 5. Calculate 14-day sales velocity from past bills and bill_items
                cur.execute(
                sql.SQL(
                    """
                SELECT COALESCE(SUM(bi.quantity), 0)
                FROM {}.bill_items bi
                JOIN {}.bills b ON bi.bill_id = b.bill_id
                WHERE bi.item_id = %s AND b.timestamp >= (NOW() - INTERVAL '14 days')
                """
                ).format(sql.Identifier(schema_name), sql.Identifier(schema_name)),
                    (item_id,)
                )
                total_units_sold = cur.fetchone()[0]
                daily_avg_sales = round(float(total_units_sold) / 14.0, 3)

                facts = {
                "tenant_id": tenant_id,
                "item": {
                    "item_id": item_id,
                    "name": item_name,
                    "brand": brand,
                    "retail_price": float(retail_price),
                    "cost_price": float(cost_price),
                    "reorder_point": reorder_point
                },
                "inventory": {
                    "quantity_on_hand": quantity_on_hand,
                    "last_updated": last_updated
                },
                "sales_velocity": {
                    "daily_average_sales_14d": daily_avg_sales,
                    "total_units_sold_last_14d": int(total_units_sold),
                    "window_days": 14
                },
                "pending_orders": pending_orders
                }
                if observation is not None:
                    observation.update(output=facts)
                return facts
        finally:
            conn.close()

@function_tool
def get_reorder_context(tenant_id: str, item_id: str) -> str:
    """
    Context-Service MCP Tool:
    Fetches real-time operational facts from mart_ai_db and makes a live MCP call to
    the KSOR server at http://127.0.0.1:8080/mcp to retrieve live governed policies.
    
    Returns:
        A JSON string containing operational inventory data, 14-day sales velocity,
        pending orders, and the live, un-cached KSOR policy text.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": f"context-{tenant_id}-{item_id}-{int(datetime.utcnow().timestamp() * 1000)}",
        "method": "tools/call",
        "params": {
            "name": "get_reorder_context",
            "arguments": {"tenant_id": tenant_id, "item_id": item_id},
        },
    }
    with current_observation(
        name="context-service-mcp-call",
        as_type="tool",
        tenant_id=tenant_id,
        item_id=item_id,
        input={"tenant_id": tenant_id, "item_id": item_id},
        metadata={"source": CONTEXT_SERVICE_MCP_URL},
    ) as observation:
        try:
            response = requests.post(
                CONTEXT_SERVICE_MCP_URL,
                headers=inject_trace_headers({
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }),
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise RuntimeError(data["error"].get("message", "Context service failed"))
            result_text = data["result"]["content"][0]["text"]
            if observation is not None:
                observation.update(output=json.loads(result_text))
            return result_text
        except Exception as exc:
            logger.error("Context service call failed at %s: %s", CONTEXT_SERVICE_MCP_URL, exc)
            error_result = {
                "error": "context_service_unavailable",
                "message": str(exc),
                "tenant_id": tenant_id,
                "item_id": item_id,
            }
            if observation is not None:
                observation.update(output=error_result, level="ERROR", status_message=str(exc))
            return json.dumps(error_result)
