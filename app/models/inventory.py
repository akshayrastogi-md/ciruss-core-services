"""
Inventory tracking models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, DateTime, Date, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
import enum
from app.models.base import TenantBaseModel


class AlertType(str, enum.Enum):
    """Stock alert types"""
    STOCKOUT_CRITICAL = "stockout_critical"  # <7 days
    STOCKOUT_HIGH = "stockout_high"  # <14 days
    STOCKOUT_MEDIUM = "stockout_medium"  # <30 days
    DEAD_STOCK = "dead_stock"  # 90+ days no sales
    SLOW_MOVING = "slow_moving"  # 60+ days slow sales


class InventorySnapshot(TenantBaseModel):
    """Daily inventory snapshot"""

    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        Index("idx_inventory_snapshot_tenant_date", "tenant_id", "date"),
        Index("idx_inventory_snapshot_product", "product_id"),
    )

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False)

    # Stock
    opening_stock = Column(Integer, default=0)
    closing_stock = Column(Integer, default=0)
    stock_in = Column(Integer, default=0)  # Purchases
    stock_out = Column(Integer, default=0)  # Sales

    # Value
    unit_cost = Column(DECIMAL(10, 2), nullable=True)
    total_value = Column(DECIMAL(12, 2), nullable=True)

    # Metrics
    days_of_inventory = Column(Integer, nullable=True)
    turnover_rate = Column(DECIMAL(5, 2), nullable=True)

    # Forecast
    forecasted_demand_7d = Column(Integer, nullable=True)
    forecasted_demand_14d = Column(Integer, nullable=True)
    forecasted_demand_30d = Column(Integer, nullable=True)

    # Stockout Prediction
    predicted_stockout_date = Column(Date, nullable=True)
    days_until_stockout = Column(Integer, nullable=True)

    # Relationship
    product = relationship("Product", foreign_keys=[product_id])


class StockAlert(TenantBaseModel):
    """Stock alert model"""

    __tablename__ = "stock_alerts"

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    # Alert Info
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low

    # Message
    message = Column(String(1000), nullable=False)

    # Stock Info
    current_stock = Column(Integer, nullable=False)
    recommended_action = Column(String(500), nullable=True)
    recommended_quantity = Column(Integer, nullable=True)

    # Dead Stock Info
    last_sale_date = Column(Date, nullable=True)
    days_since_last_sale = Column(Integer, nullable=True)
    suggested_markdown_percentage = Column(DECIMAL(5, 2), nullable=True)

    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(String(1000), nullable=True)

    # Notification
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    product = relationship("Product", foreign_keys=[product_id])
