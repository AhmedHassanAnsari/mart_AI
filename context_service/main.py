import json
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from agent.tools import get_live_ksor_policies, get_live_operational_facts
from observability import current_observation, extracted_trace_context, trace_metadata

logger = logging.getLogger("context-service")

app = FastAPI(title="Context Service", version="0.1")

TOOL_NAME = "get_reorder_context"
TOOL_DESCRIPTION = "Fetch live operational facts and governed KSOR policy for one tenant item."


def _jsonrpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


@app.post("/mcp")
def mcp(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    with extracted_trace_context(request.headers):
        return _handle_mcp(payload)


def _handle_mcp(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if method == "tools/list":
        return _jsonrpc_result(
            request_id,
            {
                "tools": [
                    {
                        "name": TOOL_NAME,
                        "description": TOOL_DESCRIPTION,
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "tenant_id": {"type": "string"},
                                "item_id": {"type": "string"},
                            },
                            "required": ["tenant_id", "item_id"],
                        },
                    }
                ]
            },
        )

    if method != "tools/call":
        return _jsonrpc_error(request_id, -32601, f"Unsupported MCP method: {method}")

    if params.get("name") != TOOL_NAME:
        return _jsonrpc_error(request_id, -32601, f"Unknown tool: {params.get('name')}")

    arguments = params.get("arguments") or {}
    tenant_id = arguments.get("tenant_id")
    item_id = arguments.get("item_id")
    if not tenant_id or not item_id:
        return _jsonrpc_error(request_id, -32602, "tenant_id and item_id are required")

    with current_observation(
        name="context-service-get-reorder-context",
        as_type="chain",
        tenant_id=tenant_id,
        item_id=item_id,
        input={"tenant_id": tenant_id, "item_id": item_id},
        metadata=trace_metadata(tenant_id, item_id),
    ) as observation:
        try:
            facts = get_live_operational_facts(tenant_id, item_id)
            policies = get_live_ksor_policies(tenant_id, item_id)
            context = {
            **facts,
            "ksor_policy": {
                "source": "http://127.0.0.1:8080/mcp",
                "reorder_policy": policies["reorder_policy"],
                "agent_permissions": policies["agent_permissions"],
            },
            }
            if observation is not None:
                observation.update(output=context)
        except Exception as exc:
            logger.exception("Context retrieval failed")
            if observation is not None:
                observation.update(level="ERROR", status_message=str(exc))
            return _jsonrpc_error(request_id, -32000, str(exc))

    return _jsonrpc_result(
        request_id,
        {"content": [{"type": "text", "text": json.dumps(context, indent=2)}]},
    )


@app.get("/")
def health() -> dict[str, str]:
    return {"service": "context-service", "status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)