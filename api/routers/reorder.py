import json
from typing import Any, Literal
from uuid import uuid4

from dapr.ext.workflow import DaprWorkflowClient
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.reorder_workflow import (
    OWNER_APPROVAL_EVENT,
    REORDER_WORKFLOW_NAME,
)
from observability import current_observation, propagate_trace_attributes, trace_metadata

router = APIRouter(prefix="/reorder", tags=["Inventory Reorder Workflow"])


class ReorderWorkflowRequest(BaseModel):
    tenant_id: str
    item_id: str


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = None


def workflow_client() -> DaprWorkflowClient:
    return DaprWorkflowClient()


def _schedule_reorder_workflow(request: ReorderWorkflowRequest, instance_id: str) -> None:
    client = workflow_client()
    try:
        client.schedule_new_workflow(
            REORDER_WORKFLOW_NAME,
            input={**request.model_dump(), "workflow_id": instance_id},
            instance_id=instance_id,
        )
    finally:
        client.close()


@router.post("/workflows")
def start_reorder_workflow(request: ReorderWorkflowRequest) -> dict[str, str]:
    instance_id = f"reorder-{uuid4()}"
    with propagate_trace_attributes(user_id=request.tenant_id, session_id=instance_id, as_baggage=True):
        with current_observation(
            name="inventory-reorder-workflow-start",
            as_type="chain",
            tenant_id=request.tenant_id,
            item_id=request.item_id,
            input=request.model_dump(),
            metadata=trace_metadata(request.tenant_id, request.item_id, workflow_id=instance_id),
        ) as observation:
            try:
                _schedule_reorder_workflow(request, instance_id)
            except Exception as exc:
                if observation is not None:
                    observation.update(level="ERROR", status_message=str(exc))
                raise HTTPException(status_code=503, detail=f"Dapr workflow unavailable: {exc}") from exc

    return {"instance_id": instance_id, "status": "started"}


@router.post("/events/inventory-reorder")
def handle_inventory_reorder_event(event: dict[str, Any]) -> dict[str, str]:
    event_data = event.get("data", event)
    if isinstance(event_data, str):
        event_data = json.loads(event_data)
    reorder_event = ReorderWorkflowRequest.model_validate(event_data)
    instance_id = f"reorder-{uuid4()}"
    with propagate_trace_attributes(
        user_id=reorder_event.tenant_id,
        session_id=instance_id,
        as_baggage=True,
    ):
        with current_observation(
            name="inventory-reorder-event",
            as_type="chain",
            tenant_id=reorder_event.tenant_id,
            item_id=reorder_event.item_id,
            input=reorder_event.model_dump(),
            metadata=trace_metadata(reorder_event.tenant_id, reorder_event.item_id, workflow_id=instance_id),
        ) as observation:
            try:
                _schedule_reorder_workflow(reorder_event, instance_id)
            except Exception as exc:
                if observation is not None:
                    observation.update(level="ERROR", status_message=str(exc))
                raise HTTPException(status_code=503, detail=f"Dapr workflow unavailable: {exc}") from exc
    return {"instance_id": instance_id, "status": "started"}


@router.get("/workflows/{instance_id}")
def get_reorder_workflow(instance_id: str) -> dict:
    client = workflow_client()
    try:
        state = client.get_workflow_state(instance_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dapr workflow unavailable: {exc}") from exc
    finally:
        client.close()

    if state is None:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    return {
        "instance_id": instance_id,
        "runtime_status": state.runtime_status,
        "workflow_state": state.serialized_output,
    }


@router.post("/approvals/{instance_id}/decision")
def decide_reorder_approval(instance_id: str, request: ApprovalDecision) -> dict[str, str]:
    with current_observation(
        name="inventory-owner-approval",
        as_type="span",
        input={"workflow_id": instance_id, "decision": request.decision},
        metadata={"workflow_id": instance_id, "approval_decision": request.decision},
    ) as observation:
      try:
        client = workflow_client()
        try:
            client.raise_workflow_event(
                instance_id,
                OWNER_APPROVAL_EVENT,
                data=request.model_dump(),
            )
        finally:
            client.close()
      except Exception as exc:
        if observation is not None:
            observation.update(level="ERROR", status_message=str(exc))
        raise HTTPException(status_code=503, detail=f"Dapr workflow unavailable: {exc}") from exc

    return {"instance_id": instance_id, "status": "decision_submitted"}