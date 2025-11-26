"""
Analytics and metrics models
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, Date, JSON, Index
from sqlalchemy.orm import relationship
from app.models.base import TenantBaseModel


class DailyMetrics(TenantBaseModel):
    """Daily aggregated metrics"""

    __tablename__ = "daily_metrics"
    __table_args__ = (
        Index("idx_daily_metrics_tenant_date", "tenant_id", "date", unique=True),
    )

    date = Column(Date, nullable=False, index=True)

    # Order Metrics
    total_orders = Column(Integer, default=0)
    total_revenue = Column(DECIMAL(12, 2), default=0)
    avg_order_value = Column(DECIMAL(10, 2), default=0)

    # Payment Method
    cod_orders = Column(Integer, default=0)
    prepaid_orders = Column(Integer, default=0)
    cod_percentage = Column(DECIMAL(5, 2), default=0)

    # Status
    confirmed_orders = Column(Integer, default=0)
    shipped_orders = Column(Integer, default=0)
    delivered_orders = Column(Integer, default=0)
    cancelled_orders = Column(Integer, default=0)
    rto_orders = Column(Integer, default=0)

    # RTO Metrics
    rto_rate = Column(DECIMAL(5, 2), default=0)
    rto_cost = Column(DECIMAL(10, 2), default=0)

    # Customer Metrics
    new_customers = Column(Integer, default=0)
    returning_customers = Column(Integer, default=0)
    repeat_purchase_rate = Column(DECIMAL(5, 2), default=0)

    # Profitability
    total_cogs = Column(DECIMAL(12, 2), default=0)
    total_profit = Column(DECIMAL(12, 2), default=0)
    profit_margin = Column(DECIMAL(5, 2), default=0)

    # Marketing
    marketing_spend = Column(DECIMAL(10, 2), default=0)
    marketing_revenue = Column(DECIMAL(10, 2), default=0)
    roas = Column(DECIMAL(10, 2), default=0)
    cac = Column(DECIMAL(10, 2), default=0)

    # Inventory
    total_inventory_value = Column(DECIMAL(12, 2), default=0)
    stockout_count = Column(Integer, default=0)


class PinCodeMetrics(TenantBaseModel):
    """Pin code performance metrics"""

    __tablename__ = "pincode_metrics"
    __table_args__ = (
        Index("idx_pincode_metrics_tenant_pincode", "tenant_id", "pincode", unique=True),
    )

    pincode = Column(String(10), nullable=False, index=True)

    # Location
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    tier = Column(String(10), nullable=True)  # 1, 2, 3

    # Order Metrics
    total_orders = Column(Integer, default=0)
    total_revenue = Column(DECIMAL(12, 2), default=0)
    avg_order_value = Column(DECIMAL(10, 2), default=0)

    # Delivery Metrics
    delivered_orders = Column(Integer, default=0)
    rto_orders = Column(Integer, default=0)
    rto_rate = Column(DECIMAL(5, 2), default=0)
    avg_delivery_days = Column(DECIMAL(5, 2), default=0)

    # Risk Score
    risk_score = Column(Integer, default=50)  # 0-100
    risk_level = Column(String(20), default="Medium")  # Low, Medium, High

    # COD Performance
    cod_orders = Column(Integer, default=0)
    cod_rto_rate = Column(DECIMAL(5, 2), default=0)

    # Last Updated
    last_order_date = Column(Date, nullable=True)
