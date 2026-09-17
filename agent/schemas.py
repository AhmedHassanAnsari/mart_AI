from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

# =====================================================================
# Context-Service MCP Tool Contract Schemas (get_reorder_context)
# =====================================================================

class ReorderContextRequest(BaseModel):
    tenant_id: str = Field(..., description="UUID string of the tenant/mart")
    item_id: str = Field(..., description="UUID string of the item needing reorder")

class ItemContext(BaseModel):
    item_id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    retail_price: float
    cost_price: float
    reorder_point: int

class InventoryContext(BaseModel):
    quantity_on_hand: int
    last_updated: Optional[str] = None

class SalesVelocityContext(BaseModel):
    daily_average_sales_14d: float = Field(
        ...,
        description="Average daily sales calculated over the 14-day window"
    )
    total_units_sold_last_14d: int = Field(
        ...,
        description="Total units sold in the 14-day window"
    )
    window_days: int = Field(default=14, description="Calculation window in days")

class PendingOrderContext(BaseModel):
    order_id: str
    quantity: int
    status: str
    created_at: Optional[str] = None
    supplier: Optional[str] = None

class KSORPolicyContext(BaseModel):
    source: str = Field(
        default="http://127.0.0.1:8080/mcp",
        description="Origin of the live KSOR policy data"
    )
    reorder_policy: str = Field(
        ...,
        description="Live policy text fetched on-demand from KSOR for reordering rules and quantity formulas"
    )
    agent_permissions: str = Field(
        ...,
        description="Live policy text fetched on-demand from KSOR for blast-radius limits and approval gates"
    )
    raw_citations: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Citations, trust tiers, and governance metadata returned by KSOR"
    )

class ReorderContextResponse(BaseModel):
    tenant_id: str
    item: ItemContext
    inventory: InventoryContext
    sales_velocity: SalesVelocityContext
    pending_orders: List[PendingOrderContext] = Field(default_factory=list)
    ksor_policy: KSORPolicyContext


# =====================================================================
# Inventory Agent Decision Output Schema
# =====================================================================

class ReorderDecision(BaseModel):
    tenant_id: str = Field(..., description="ID of the tenant/mart")
    item_id: str = Field(..., description="ID of the item evaluated")
    item_name: str = Field(..., description="Name of the item evaluated")
    decision: Literal["order", "do_not_order", "escalate"] = Field(
        ...,
        description="Final action decided by LLM: order autonomously, do not order, or escalate to Mart Owner"
    )
    quantity_to_order: int = Field(
        ...,
        description="Quantity determined to order, or 0 if not ordering"
    )
    supplier: Optional[str] = Field(
        None,
        description="Chosen trusted supplier (per category match and frequency) or None if escalated"
    )
    estimated_total_cost: float = Field(
        ...,
        description="Total order value calculated: quantity_to_order * item.cost_price"
    )
    within_blast_radius: bool = Field(
        ...,
        description="True if estimated_total_cost <= the dynamic autonomous limit from live KSOR policy"
    )
    escalate_to_owner: bool = Field(
        ...,
        description="True if human Mart Owner approval is mandatory per dynamic KSOR rules"
    )
    reasoning: str = Field(
        ...,
        description="Full explanation citing current inventory, sales velocity, pending orders, and the dynamic KSOR policies"
    )
