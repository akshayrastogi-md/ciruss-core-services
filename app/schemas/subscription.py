"""
Subscription schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from decimal import Decimal


class SubscriptionPlanResponse(BaseModel):
    """Subscription plan response"""

    id: int
    name: str
    slug: str
    price: Decimal
    billing_period: str
    max_channels: Optional[int] = None
    max_orders: Optional[int] = None
    features: dict
    is_active: bool

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """Create subscription request"""

    plan_id: int
    razorpay_payment_method_id: Optional[str] = None


class SubscriptionResponse(BaseModel):
    """Subscription response"""

    id: int
    tenant_id: int
    plan_id: int
    plan_name: str
    razorpay_subscription_id: Optional[str] = None
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionUsage(BaseModel):
    """Current subscription usage"""

    plan_name: str
    max_channels: Optional[int] = None
    current_channels: int
    max_orders: Optional[int] = None
    current_orders: int
    usage_percentage: Decimal
    is_overaged: bool
    overage_amount: int = Field(default=0)


class InvoiceResponse(BaseModel):
    """Invoice response"""

    id: int
    subscription_id: int
    invoice_number: str
    razorpay_invoice_id: Optional[str] = None
    amount: Decimal
    tax: Decimal
    total: Decimal
    status: str
    invoice_date: datetime
    due_date: datetime
    paid_at: Optional[datetime] = None
    invoice_url: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionCancel(BaseModel):
    """Cancel subscription request"""

    cancel_at_period_end: bool = Field(default=True)
    reason: Optional[str] = None
