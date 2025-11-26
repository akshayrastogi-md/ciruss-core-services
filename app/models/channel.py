"""
Channel integration models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
import enum
from app.models.base import TenantBaseModel


class ChannelType(str, enum.Enum):
    """Channel types"""
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    AMAZON = "amazon"
    FLIPKART = "flipkart"
    MANUAL = "manual"


class Channel(TenantBaseModel):
    """E-commerce channel model"""

    __tablename__ = "channels"

    name = Column(String(255), nullable=False)
    channel_type = Column(SQLEnum(ChannelType), nullable=False)
    store_url = Column(String(500), nullable=True)

    # Connection Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String(50), nullable=True)  # success, failed, in_progress

    # Sync Settings
    auto_sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=30)
    webhook_enabled = Column(Boolean, default=False)

    # Metadata
    channel_metadata = Column(JSON, default={})  # Store channel-specific data

    # Relationships
    tenant = relationship("Tenant", back_populates="channels")
    credentials = relationship("ChannelCredentials", back_populates="channel", uselist=False)
    orders = relationship("Order", back_populates="channel")


class ChannelCredentials(TenantBaseModel):
    """Encrypted channel credentials"""

    __tablename__ = "channel_credentials"

    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Encrypted credentials (stored as encrypted JSON)
    encrypted_credentials = Column(Text, nullable=False)

    # OAuth tokens (if applicable)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    channel = relationship("Channel", back_populates="credentials")
