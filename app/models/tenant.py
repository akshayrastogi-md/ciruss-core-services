"""
Tenant models for multi-tenancy
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Tenant(BaseModel):
    """Tenant/Organization model"""

    __tablename__ = "tenants"

    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    gstin = Column(String(15), nullable=True)  # GST Identification Number
    pan = Column(String(10), nullable=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), default="India")

    # Settings
    timezone = Column(String(50), default="Asia/Kolkata")
    currency = Column(String(10), default="INR")

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    channels = relationship("Channel", back_populates="tenant", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="tenant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="tenant", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="tenant", uselist=False)


class TenantSettings(BaseModel):
    """Tenant-specific settings"""

    __tablename__ = "tenant_settings"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)

    # COD/RTO Settings
    cod_auto_accept_threshold = Column(Integer, default=70)  # Risk score threshold
    cod_auto_reject_threshold = Column(Integer, default=30)
    rto_cost_percentage = Column(Integer, default=100)  # % of order value

    # Inventory Settings
    safety_stock_service_level = Column(Integer, default=95)  # 95%
    inventory_holding_cost_annual = Column(Integer, default=25)  # 25%

    # Tax Settings
    tax_enabled = Column(Boolean, default=True)
    tcs_enabled = Column(Boolean, default=True)
    tcs_rate = Column(Integer, default=1)  # 1%

    # Notification Settings
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    whatsapp_notifications = Column(Boolean, default=False)

    # Custom Settings (JSON)
    custom_settings = Column(JSON, default={})

    # Relationship
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
