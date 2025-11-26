"""
Marketing and advertising models
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, Date, JSON, Index
from sqlalchemy.orm import relationship
import enum
from app.models.base import TenantBaseModel


class MarketingChannel(str, enum.Enum):
    """Marketing channel types"""
    FACEBOOK = "facebook"
    GOOGLE = "google"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"
    ORGANIC = "organic"
    DIRECT = "direct"
    REFERRAL = "referral"
    EMAIL = "email"


class MarketingCampaign(TenantBaseModel):
    """Marketing campaign model"""

    __tablename__ = "marketing_campaigns"
    __table_args__ = (
        Index("idx_campaign_tenant_channel", "tenant_id", "channel"),
    )

    # Campaign Info
    campaign_id = Column(String(255), nullable=False)  # External campaign ID
    campaign_name = Column(String(500), nullable=False)
    channel = Column(String(50), nullable=False)  # facebook, google, etc.

    # Status
    status = Column(String(50), nullable=False)  # active, paused, completed

    # Dates
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Metadata
    campaign_metadata = Column(JSON, default={})  # Store platform-specific data

    # Relationships
    ad_spends = relationship("AdSpend", back_populates="campaign", cascade="all, delete-orphan")


class AdSpend(TenantBaseModel):
    """Daily ad spend and performance metrics"""

    __tablename__ = "ad_spends"
    __table_args__ = (
        Index("idx_adspend_tenant_date", "tenant_id", "date"),
        Index("idx_adspend_campaign", "campaign_id"),
    )

    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=True)

    # Date
    date = Column(Date, nullable=False, index=True)

    # Channel
    channel = Column(String(50), nullable=False)

    # Metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(DECIMAL(10, 2), default=0)
    conversions = Column(Integer, default=0)
    revenue = Column(DECIMAL(10, 2), default=0)

    # Calculated Metrics
    ctr = Column(DECIMAL(5, 2), default=0)  # Click-through rate
    cpc = Column(DECIMAL(10, 2), default=0)  # Cost per click
    cpa = Column(DECIMAL(10, 2), default=0)  # Cost per acquisition
    roas = Column(DECIMAL(10, 2), default=0)  # Return on ad spend

    # Attribution
    attributed_orders = Column(Integer, default=0)
    attributed_revenue = Column(DECIMAL(10, 2), default=0)

    # Metadata
    ad_metadata = Column(JSON, default={})

    # Relationship
    campaign = relationship("MarketingCampaign", back_populates="ad_spends")
