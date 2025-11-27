"""
Analytics schemas
"""
from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from decimal import Decimal


class DashboardMetrics(BaseModel):
    """Dashboard overview metrics"""

    total_revenue: Decimal = Field(default=Decimal("0"))
    total_orders: int = Field(default=0)
    average_order_value: Decimal = Field(default=Decimal("0"))
    profit_margin: Decimal = Field(default=Decimal("0"))
    rto_rate: Decimal = Field(default=Decimal("0"))
    cod_percentage: Decimal = Field(default=Decimal("0"))
    active_skus: int = Field(default=0)
    marketing_spend: Decimal = Field(default=Decimal("0"))
    roas: Decimal = Field(default=Decimal("0"))

    # Change metrics (vs previous period)
    revenue_change: Decimal = Field(default=Decimal("0"))
    orders_change: Decimal = Field(default=Decimal("0"))
    aov_change: Decimal = Field(default=Decimal("0"))

    class Config:
        from_attributes = True


class RevenueDataPoint(BaseModel):
    """Revenue data point for charts"""

    date: date
    revenue: Decimal
    orders: int
    forecast: Optional[Decimal] = None

    class Config:
        from_attributes = True


class ChannelPerformance(BaseModel):
    """Channel-wise performance metrics"""

    channel_id: int
    channel_name: str
    channel_type: str
    revenue: Decimal
    orders: int
    percentage: Decimal

    class Config:
        from_attributes = True


class ProductPerformance(BaseModel):
    """Product performance metrics"""

    product_id: int
    product_name: str
    sku: str
    revenue: Decimal
    quantity_sold: int

    class Config:
        from_attributes = True


class StateRevenue(BaseModel):
    """State-wise revenue"""

    state: str
    revenue: Decimal
    orders: int

    class Config:
        from_attributes = True


class PaymentMethodDistribution(BaseModel):
    """Payment method distribution"""

    method: str
    count: int
    percentage: Decimal

    class Config:
        from_attributes = True


class OrderStatusDistribution(BaseModel):
    """Order status distribution"""

    status: str
    count: int
    percentage: Decimal

    class Config:
        from_attributes = True


class CustomerMetrics(BaseModel):
    """Customer analytics metrics"""

    new_customers: int
    returning_customers: int
    repeat_purchase_rate: Decimal
    total_customers: int

    class Config:
        from_attributes = True


class MarketingMetrics(BaseModel):
    """Marketing performance metrics"""

    total_spend: Decimal
    total_revenue: Decimal
    blended_roas: Decimal
    cac: Decimal
    new_customers: int
    ltv_cac_ratio: Decimal

    class Config:
        from_attributes = True


class ChannelMarketingPerformance(BaseModel):
    """Channel-wise marketing performance"""

    channel: str
    spend: Decimal
    revenue: Decimal
    roas: Decimal
    impressions: int
    clicks: int
    conversions: int
    ctr: Decimal
    cpc: Decimal

    class Config:
        from_attributes = True


class DailyMetricsResponse(BaseModel):
    """Daily metrics response"""

    date: date
    revenue: Decimal
    orders: int
    confirmed_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int
    rto_orders: int
    cod_orders: int
    prepaid_orders: int
    cod_percentage: Decimal
    rto_rate: Decimal
    rto_cost: Decimal
    new_customers: int
    returning_customers: int
    repeat_purchase_rate: Decimal
    cogs: Decimal
    profit: Decimal
    profit_margin: Decimal
    marketing_spend: Decimal
    marketing_revenue: Decimal
    marketing_roas: Decimal
    cac: Decimal
    inventory_value: Decimal
    stockouts: int

    class Config:
        from_attributes = True


class PinCodeMetricsResponse(BaseModel):
    """Pin code metrics response"""

    pincode: str
    city: Optional[str] = None
    state: Optional[str] = None
    tier: Optional[str] = None
    total_orders: int
    delivered_orders: int
    rto_orders: int
    rto_rate: Decimal
    delivery_success_rate: Decimal
    risk_score: int
    risk_level: str
    cod_orders: int
    cod_percentage: Decimal
    avg_order_value: Decimal
    avg_delivery_days: Decimal
    last_updated: datetime

    class Config:
        from_attributes = True


class CODRTOAnalytics(BaseModel):
    """COD/RTO analytics"""

    # Overall metrics
    overall_rto_rate: Decimal
    cod_rto_rate: Decimal
    prepaid_rto_rate: Decimal
    total_rto_cost: Decimal

    # Breakdown by channel
    channel_breakdown: List[Dict]

    # Breakdown by courier
    courier_breakdown: List[Dict]

    # Breakdown by category
    category_breakdown: List[Dict]

    # Pin code risk distribution
    high_risk_pincodes: int
    medium_risk_pincodes: int
    low_risk_pincodes: int

    # NDR metrics
    total_ndr: int
    ndr_resolved: int
    ndr_pending: int
    ndr_resolution_rate: Decimal

    class Config:
        from_attributes = True


class InventoryAnalytics(BaseModel):
    """Inventory analytics"""

    # Overall metrics
    total_inventory_value: Decimal
    total_skus: int
    active_skus: int

    # Days of inventory
    avg_doi: Decimal

    # Inventory turnover
    inventory_turnover_ratio: Decimal

    # Holding costs
    annual_holding_cost_percentage: Decimal
    estimated_holding_cost: Decimal

    # Stock alerts
    critical_stockouts: int  # <7 days
    high_stockouts: int  # <14 days
    medium_stockouts: int  # <30 days

    # Dead stock
    dead_stock_items: int  # 90+ days no sales
    very_slow_moving: int  # 60-90 days
    slow_moving: int  # 30-60 days
    dead_stock_value: Decimal

    class Config:
        from_attributes = True


class SKUProfitability(BaseModel):
    """SKU-level profitability"""

    product_id: int
    product_name: str
    sku: str
    revenue: Decimal
    cogs: Decimal
    platform_fees: Decimal
    payment_gateway_fees: Decimal
    shipping_cost: Decimal
    rto_cost: Decimal
    marketing_cost: Decimal
    net_profit: Decimal
    profit_margin: Decimal
    units_sold: int

    class Config:
        from_attributes = True


class WorkingCapitalMetrics(BaseModel):
    """Working capital insights"""

    # COD remittances
    pending_cod_shopify: Decimal
    pending_cod_woocommerce: Decimal
    pending_cod_amazon: Decimal
    pending_cod_flipkart: Decimal
    total_pending_cod: Decimal

    # Expected remittances
    expected_7_days: Decimal
    expected_14_days: Decimal
    expected_30_days: Decimal

    # Cash flow forecast
    projected_cash_balance_7d: Decimal
    projected_cash_balance_14d: Decimal
    projected_cash_balance_30d: Decimal
    working_capital_runway_days: int

    # Reconciliation status
    unreconciled_orders: int
    amount_mismatch: Decimal
    pending_reconciliation: int

    class Config:
        from_attributes = True


class ForecastData(BaseModel):
    """Demand forecast data"""

    date: date
    forecasted_demand: Decimal
    lower_bound: Optional[Decimal] = None
    upper_bound: Optional[Decimal] = None
    confidence: Optional[Decimal] = None

    class Config:
        from_attributes = True


class FestivalForecast(BaseModel):
    """Festival-specific forecast"""

    festival_name: str
    festival_date: date
    category: str
    expected_demand_multiplier: Decimal
    forecasted_orders: int
    recommended_stock: int

    class Config:
        from_attributes = True


class StockoutPrediction(BaseModel):
    """Stockout prediction"""

    product_id: int
    product_name: str
    sku: str
    current_stock: int
    predicted_stockout_date: date
    days_until_stockout: int
    severity: str  # Critical, High, Medium
    recommended_reorder_qty: int

    class Config:
        from_attributes = True
