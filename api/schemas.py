from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

# --- Tenant Onboarding ---

class TenantCreate(BaseModel):
    mart_name: str
    address: Optional[str] = None
    operating_hours: Optional[Dict] = Field(
        default=None,
        description="JSONB: {'default': '09:00-21:00', 'overrides': {'Saturday': '10:00-20:00'}}"
    )
    owner_name: Optional[str] = None
    contact_info: Optional[str] = None

class TenantResponse(BaseModel):
    tenant_id: UUID
    schema_name: str
    status: str

# --- Checkout ---

class CheckoutItem(BaseModel):
    item_id: UUID
    quantity: int
    sale_price: float

class CheckoutRequest(BaseModel):
    tenant_id: UUID
    items: List[CheckoutItem]
    timestamp: Optional[datetime] = None

class CheckoutResponse(BaseModel):
    bill_id: UUID
    total_price: float
    status: str

# --- Authentication ---

class UserSignup(BaseModel):
    email: str
    password: str
    profile_info: Optional[Dict] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class UserResponse(BaseModel):
    customer_id: UUID
    email: str
