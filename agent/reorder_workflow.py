from datetime import timedelta
from typing import Any

from dapr.ext.workflow import (
    DaprWorkflowContext,
    RetryPolicy,
    WorkflowActivityContext,
    WorkflowRuntime,
)

from agent.inventory_agent import handle_wake_event
import os

from observability import current_observation, propagate_trace_attributes, trace_metadata

OWNER_APPROVAL_EVENT = "owner-approval"
REORDER_WORKFLOW_NAME = "inventory-reorder-workflow"
MAKE_DECISION_ACTIVITY_NAME = "make-reorder-decision"

retry_policy = RetryPolicy(
    first_retry_interval=timedelta(seconds=5),
    max_number_of_attempts=3,
    backoff_coefficient=2.0,
)


async def make_reorder_decision(
    context: WorkflowActivityContext,
    request: dict[str, str],
) -> dict[str, Any]:
    """Run the existing agent decision as a retryable workflow activity."""
    tenant_id = request["tenant_id"]
    item_id = request["item_id"]
    workflow_id = request.get("workflow_id", context.workflow_id)
    with propagate_trace_attributes(
        user_id=tenant_id,
        session_id=workflow_id,
        environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"),
        as_baggage=True,
    ):
        with current_observation(
            name="inventory-reorder-decision",
            as_type="chain",
            tenant_id=tenant_id,
            item_id=item_id,
            input={"tenant_id": tenant_id, "item_id": item_id},
            metadata=trace_metadata(
                tenant_id,
                item_id,
                workflow_id=workflow_id,
                user_id=tenant_id,
                session_id=workflow_id,
            ),
        ) as observation:
            decision = await handle_wake_event(tenant_id, item_id)
            output = decision.model_dump(mode="json")
            if observation is not None:
                observation.update(output=output)
            return output


def inventory_reorder_workflow(
    context: DaprWorkflowContext,
    request: dict[str, str],
):
    decision = yield context.call_activity(
        MAKE_DECISION_ACTIVITY_NAME,
        input=request,
        retry_policy=retry_policy,
    )

    if decision.get("decision") != "escalate" and not decision.get("escalate_to_owner"):
        return {"status": "completed", "decision": decision}

    approval = yield context.wait_for_external_event(OWNER_APPROVAL_EVENT)
    if approval.get("decision") != "approve":
        return {
            "status": "rejected",
            "decision": decision,
            "approval": approval,
        }

    return {
        "status": "approved",
        "decision": decision,
        "approval": approval,
    }


def create_workflow_runtime() -> WorkflowRuntime:
    runtime = WorkflowRuntime()
    runtime.register_workflow(inventory_reorder_workflow, name=REORDER_WORKFLOW_NAME)
    runtime.register_activity(make_reorder_decision, name=MAKE_DECISION_ACTIVITY_NAME)
    return runtime