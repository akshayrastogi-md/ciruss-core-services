"""
Order models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, DateTime, Enum as SQLEnum, Text, JSON, Index
from sqlalchemy.orm import relationship
import enum
from app.models.base import TenantBaseModel


class OrderStatus(str, enum.Enum):
    """Order status types"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RTO_INITIATED = "rto_initiated"
    RTO_DELIVERED = "rto_delivered"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    """Payment method types"""
    COD = "cod"
    PREPAID = "prepaid"
    UPI = "upi"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    NET_BANKING = "net_banking"
    WALLET = "wallet"


class Order(TenantBaseModel):
    """Order model"""

    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_order_tenant_status", "tenant_id", "status"),
        Index("idx_order_tenant_date", "tenant_id", "order_date"),
        Index("idx_order_channel", "channel_id"),
    )

    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)

    # Order Info
    order_number = Column(String(100), nullable=False, index=True)
    external_order_id = Column(String(255), nullable=True)  # Channel's order ID
    order_date = Column(DateTime(timezone=True), nullable=False)

    # Status
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)

    # Customer Info
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(20), nullable=False)
    customer_type = Column(String(50), default="new")  # new, returning

    # Shipping Address
    shipping_address_line1 = Column(String(255), nullable=False)
    shipping_address_line2 = Column(String(255), nullable=True)
    shipping_city = Column(String(100), nullable=False)
    shipping_state = Column(String(100), nullable=False)
    shipping_pincode = Column(String(10), nullable=False, index=True)
    shipping_country = Column(String(100), default="India")

    # Billing Address
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(100), nullable=True)
    billing_pincode = Column(String(10), nullable=True)
    billing_country = Column(String(100), default="India")

    # Payment
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    payment_status = Column(String(50), default="pending")  # pending, paid, failed, refunded

    # Amounts
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    discount_amount = Column(DECIMAL(10, 2), default=0)
    shipping_charges = Column(DECIMAL(10, 2), default=0)
    tax_amount = Column(DECIMAL(10, 2), default=0)
    total_amount = Column(DECIMAL(10, 2), nullable=False)

    # GST Breakdown
    cgst_amount = Column(DECIMAL(10, 2), default=0)
    sgst_amount = Column(DECIMAL(10, 2), default=0)
    igst_amount = Column(DECIMAL(10, 2), default=0)
    tcs_amount = Column(DECIMAL(10, 2), default=0)

    # Costs & Profitability
    cogs = Column(DECIMAL(10, 2), default=0)  # Cost of Goods Sold
    platform_fee = Column(DECIMAL(10, 2), default=0)
    payment_gateway_fee = Column(DECIMAL(10, 2), default=0)
    shipping_cost = Column(DECIMAL(10, 2), default=0)
    rto_cost = Column(DECIMAL(10, 2), default=0)
    marketing_cost = Column(DECIMAL(10, 2), default=0)  # Attribution
    net_profit = Column(DECIMAL(10, 2), default=0)

    # RTO Prediction
    rto_risk_score = Column(Integer, nullable=True)  # 0-100
    rto_risk_level = Column(String(20), nullable=True)  # Low, Medium, High
    rto_probability = Column(DECIMAL(5, 4), nullable=True)  # 0-1

    # COD Acceptance
    cod_acceptance_decision = Column(String(50), nullable=True)  # auto_accept, manual_review, auto_reject
    cod_manual_override = Column(Boolean, default=False)

    # Attribution
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    utm_term = Column(String(100), nullable=True)
    utm_content = Column(String(100), nullable=True)
    gclid = Column(String(255), nullable=True)  # Google Click ID
    fbclid = Column(String(255), nullable=True)  # Facebook Click ID

    # Metadata
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=[])
    custom_fields = Column(JSON, default={})

    # Timestamps
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="orders")
    channel = relationship("Channel", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipment = relationship("Shipment", back_populates="order", uselist=False)


class OrderItem(TenantBaseModel):
    """Order item model"""

    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)

    # Product Info (snapshot at order time)
    product_name = Column(String(500), nullable=False)
    sku = Column(String(100), nullable=False)
    variant_name = Column(String(500), nullable=True)

    # Pricing
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    discount = Column(DECIMAL(10, 2), default=0)
    tax_rate = Column(DECIMAL(5, 2), default=18.00)
    tax_amount = Column(DECIMAL(10, 2), default=0)
    total_amount = Column(DECIMAL(10, 2), nullable=False)

    # Cost
    unit_cost = Column(DECIMAL(10, 2), nullable=True)  # COGS per unit

    # GST
    hsn_code = Column(String(8), nullable=True)
    cgst_amount = Column(DECIMAL(10, 2), default=0)
    sgst_amount = Column(DECIMAL(10, 2), default=0)
    igst_amount = Column(DECIMAL(10, 2), default=0)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
