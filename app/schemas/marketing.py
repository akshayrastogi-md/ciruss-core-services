"""
Marketing schemas
"""
from datetime import datetime, date
from typing import Optional, Dict
from pydantic import BaseModel, Field
from decimal import Decimal


class MarketingCampaignResponse(BaseModel):
    """Marketing campaign response"""

    id: int
    platform: str  # facebook, google
    campaign_id: str
    campaign_name: str
    status: str
    objective: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdSpendResponse(BaseModel):
    """Ad spend response"""

    id: int
    campaign_id: int
    campaign_name: str
    platform: str
    date: date
    spend: Decimal
    impressions: int
    clicks: int
    conversions: int
    revenue: Decimal
    roas: Decimal
    cpc: Decimal
    ctr: Decimal
    cpa: Decimal

    class Config:
        from_attributes = True


class CampaignPerformance(BaseModel):
    """Campaign performance summary"""

    campaign_id: int
    campaign_name: str
    platform: str
    total_spend: Decimal
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_revenue: Decimal
    roas: Decimal
    avg_cpc: Decimal
    avg_ctr: Decimal
    avg_cpa: Decimal

    class Config:
        from_attributes = True


class AttributionData(BaseModel):
    """Attribution tracking data"""

    channel: str
    first_click_revenue: Decimal
    last_click_revenue: Decimal
    multi_touch_revenue: Decimal
    conversions: int

    class Config:
        from_attributes = True


class CALTVMetrics(BaseModel):
    """CAC and LTV metrics"""

    total_customers: int
    new_customers: int
    acquisition_cost: Decimal
    cac: Decimal
    avg_ltv: Decimal
    ltv_cac_ratio: Decimal
    payback_period_days: int

    class Config:
        from_attributes = True


class FacebookAdsSync(BaseModel):
    """Facebook Ads sync request"""

    ad_account_id: str
    access_token: str
    start_date: date
    end_date: date


class GoogleAdsSync(BaseModel):
    """Google Ads sync request"""

    customer_id: str
    access_token: str
    refresh_token: str
    start_date: date
    end_date: date
