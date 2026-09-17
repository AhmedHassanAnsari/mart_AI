import json
import logging
from typing import Optional, Dict, Any
from agents import Agent, Runner, AgentOutputSchema
from agent.config import get_model, get_model_name
from agent.schemas import ReorderDecision
from agent.tools import get_reorder_context
from observability import current_observation, trace_metadata

logger = logging.getLogger("inventory-agent")

INVENTORY_AGENT_INSTRUCTIONS = """
You are the autonomous Inventory Agent for the AI Workforce Orchestrator platform.
You are woken by an event carrying a `tenant_id` (mart identifier) and an `item_id` (the item whose inventory dropped below the reorder point).

YOUR MANDATE:
1. Context Retrieval:
   - Immediately call `get_reorder_context(tenant_id, item_id)` to retrieve live operational facts from the database and live governed policies from KSOR.
   - If the context tool reports an error (e.g. context service or database unavailable), you CANNOT make an autonomous decision. Set:
     `decision="escalate"`, `escalate_to_owner=True`, `quantity_to_order=0`, `estimated_total_cost=0.0`, `supplier=None`, and document the service failure in `reasoning`.

2. Dynamic Policy Interpretation:
   - Treat the `ksor_policy` object returned by the context tool as the sole source of policy.
   - Do not use a policy threshold, formula, monetary limit, supplier rule, or permission scope from these instructions or from prior context.

3. Decision & Reasoning Workflow:
   a. Check Pending Orders:
      - If existing pending orders already satisfy the reorder requirement, do not place duplicate orders. Set `decision="do_not_order"`, `quantity_to_order=0`, `estimated_total_cost=0.0`, `supplier=None`, `escalate_to_owner=False`.
   b. Calculate Quantity:
      - Apply the formula stated in the live `reorder_policy` against the sales velocity (units sold in window).
      - Compute `estimated_total_cost = quantity_to_order * item.cost_price`.
   c. Evaluate Blast Radius:
      - Extract the autonomous order limit from the live `agent_permissions` text.
      - If `estimated_total_cost > autonomous_limit`:
        The order exceeds the autonomous blast radius. Set `within_blast_radius=False`, `escalate_to_owner=True`, `decision="escalate"`. Explicitly state the dynamic threshold exceeded in `reasoning`.
      - If `estimated_total_cost <= autonomous_limit`:
        The order is safe to execute autonomously. Set `within_blast_radius=True`, `escalate_to_owner=False`, `decision="order"`.
   d. Select Supplier:
      - Select a supplier strictly in accordance with the supplier rules in the live `ksor_policy`.
      - If no authorized/trusted supplier is available, escalate to the Mart Owner (`decision="escalate"`, `escalate_to_owner=True`, `supplier=None`).

4. Output Structure:
   Always return a complete ReorderDecision structured object populating all fields:
   `tenant_id`, `item_id`, `item_name`, `decision`, `quantity_to_order`, `supplier`, `estimated_total_cost`, `within_blast_radius`, `escalate_to_owner`, and `reasoning`.
"""

def create_inventory_agent() -> Agent:
    """Instantiates the Inventory Agent with Gemini models and the live context tool."""
    model = get_model()
    return Agent(
        name="InventoryAgent",
        model=model,
        instructions=INVENTORY_AGENT_INSTRUCTIONS,
        tools=[get_reorder_context],
        output_type=AgentOutputSchema(ReorderDecision, strict_json_schema=False),
    )

async def handle_wake_event(
    tenant_id: str,
    item_id: str,
) -> ReorderDecision:
    """Run the Inventory agent for one tenant/item wake event."""
    agent = create_inventory_agent()
    input_message = f"Wake event received. Evaluate reorder for tenant_id: '{tenant_id}', item_id: '{item_id}'."

    logger.info(f"Running Inventory Agent for tenant {tenant_id}, item {item_id}...")
    with current_observation(
        name="inventory-agent",
        as_type="agent",
        tenant_id=tenant_id,
        item_id=item_id,
        input={"tenant_id": tenant_id, "item_id": item_id},
        model=get_model_name(),
        metadata=trace_metadata(tenant_id, item_id, model=get_model_name()),
    ) as observation:
        result = await Runner.run(agent, input=input_message)
        decision = result.final_output
        if observation is not None:
            observation.update(output=decision.model_dump(mode="json"))
        return decision
