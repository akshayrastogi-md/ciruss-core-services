"""
Database models
"""
from app.models.tenant import Tenant, TenantSettings
from app.models.user import User, Role, UserRole, APIKey
from app.models.channel import Channel, ChannelType, ChannelCredentials
from app.models.product import Product, ProductVariant, HSNCode
from app.models.order import Order, OrderItem, OrderStatus
from app.models.shipment import Shipment, ShipmentStatus, NDRReport
from app.models.marketing import MarketingCampaign, MarketingChannel, AdSpend
from app.models.subscription import Subscription, SubscriptionPlan, Invoice
from app.models.analytics import DailyMetrics, PinCodeMetrics
from app.models.report import Report, ReportSchedule
from app.models.ml_model import MLModel, MLPrediction
from app.models.inventory import InventorySnapshot, StockAlert
from app.models.payment import PaymentReconciliation, CODRemittance

__all__ = [
    # Tenant
    "Tenant",
    "TenantSettings",
    # User & Auth
    "User",
    "Role",
    "UserRole",
    "APIKey",
    # Channel
    "Channel",
    "ChannelType",
    "ChannelCredentials",
    # Product
    "Product",
    "ProductVariant",
    "HSNCode",
    # Order
    "Order",
    "OrderItem",
    "OrderStatus",
    # Shipment
    "Shipment",
    "ShipmentStatus",
    "NDRReport",
    # Marketing
    "MarketingCampaign",
    "MarketingChannel",
    "AdSpend",
    # Subscription
    "Subscription",
    "SubscriptionPlan",
    "Invoice",
    # Analytics
    "DailyMetrics",
    "PinCodeMetrics",
    # Reports
    "Report",
    "ReportSchedule",
    # ML
    "MLModel",
    "MLPrediction",
    # Inventory
    "InventorySnapshot",
    "StockAlert",
    # Payment
    "PaymentReconciliation",
    "CODRemittance",
]
