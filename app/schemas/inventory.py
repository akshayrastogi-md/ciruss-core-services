"""
Inventory schemas
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field
from decimal import Decimal


class InventorySnapshotResponse(BaseModel):
    """Inventory snapshot response"""

    id: int
    product_variant_id: int
    product_name: str
    sku: str
    quantity: int
    unit_cost: Decimal
    total_value: Decimal
    snapshot_date: datetime

    class Config:
        from_attributes = True


class StockAlertResponse(BaseModel):
    """Stock alert response"""

    id: int
    product_variant_id: int
    product_name: str
    sku: str
    alert_type: str
    current_stock: int
    predicted_stockout_date: Optional[date] = None
    days_until_stockout: Optional[int] = None
    recommended_reorder_qty: Optional[int] = None
    severity: str
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DeadStockAnalysis(BaseModel):
    """Dead stock analysis"""

    product_variant_id: int
    product_name: str
    sku: str
    current_stock: int
    days_since_last_sale: int
    stock_value: Decimal
    classification: str  # Dead, Very Slow, Slow Moving
    aging_bracket: str  # 0-30, 30-60, 60-90, 90-180, 180+
    recommended_markdown: Decimal
    recommended_clearance_price: Decimal

    class Config:
        from_attributes = True


class SafetyStockCalculation(BaseModel):
    """Safety stock calculation"""

    product_variant_id: int
    product_name: str
    sku: str
    avg_daily_demand: Decimal
    demand_std_dev: Decimal
    lead_time_days: int
    service_level: Decimal
    safety_stock: int
    reorder_point: int
    economic_order_quantity: int

    class Config:
        from_attributes = True


class InventoryTurnoverAnalysis(BaseModel):
    """Inventory turnover analysis"""

    product_variant_id: int
    product_name: str
    sku: str
    avg_inventory_value: Decimal
    cogs: Decimal
    inventory_turnover_ratio: Decimal
    days_of_inventory: Decimal
    performance_rating: str  # Excellent, Good, Average, Poor

    class Config:
        from_attributes = True
