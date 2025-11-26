"""
Subscription and billing models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
import enum
from app.models.base import BaseModel


class PlanType(str, enum.Enum):
    """Subscription plan types"""
    TRIAL = "trial"
    STARTER = "starter"
    GROWTH = "growth"
    PROFESSIONAL = "professional"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status types"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SubscriptionPlan(BaseModel):
    """Subscription plan model"""

    __tablename__ = "subscription_plans"

    name = Column(SQLEnum(PlanType), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    price = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(10), default="INR")
    billing_period = Column(String(20), default="monthly")  # monthly, yearly

    # Limits
    max_channels = Column(Integer, nullable=False)
    max_orders_per_month = Column(Integer, nullable=False)
    max_users = Column(Integer, default=5)

    # Features
    features = Column(Text, nullable=True)  # JSON string

    # Status
    is_active = Column(Boolean, default=True)

    # Razorpay
    razorpay_plan_id = Column(String(255), nullable=True)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(BaseModel):
    """Subscription model"""

    __tablename__ = "subscriptions"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)

    # Status
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)

    # Dates
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    trial_end_date = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Billing
    next_billing_date = Column(DateTime(timezone=True), nullable=True)
    last_billing_date = Column(DateTime(timezone=True), nullable=True)

    # Usage Tracking
    current_period_orders = Column(Integer, default=0)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)

    # Razorpay
    razorpay_subscription_id = Column(String(255), nullable=True, unique=True)
    razorpay_customer_id = Column(String(255), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")


class Invoice(BaseModel):
    """Invoice model"""

    __tablename__ = "invoices"

    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)

    # Invoice Info
    invoice_number = Column(String(100), unique=True, nullable=False)
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)

    # Amounts
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    tax_amount = Column(DECIMAL(10, 2), default=0)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(10), default="INR")

    # Status
    status = Column(String(50), default="pending")  # pending, paid, failed, refunded
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Razorpay
    razorpay_invoice_id = Column(String(255), nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)

    # PDF
    pdf_url = Column(String(1000), nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
