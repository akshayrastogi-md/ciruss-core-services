"""
Marketing endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from datetime import date, timedelta, datetime
from decimal import Decimal

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.marketing import MarketingCampaign, AdSpend
from app.schemas.marketing import (
    MarketingCampaignResponse,
    AdSpendResponse,
    CampaignPerformance,
    FacebookAdsSync,
    GoogleAdsSync,
    CALTVMetrics,
)

router = APIRouter()


@router.get("/campaigns", response_model=List[MarketingCampaignResponse])
async def list_campaigns(
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List marketing campaigns

    Returns all marketing campaigns from Facebook Ads and Google Ads.
    """
    conditions = [MarketingCampaign.tenant_id == current_user.tenant_id]

    if platform:
        conditions.append(MarketingCampaign.platform == platform)

    if status:
        conditions.append(MarketingCampaign.status == status)

    query = (
        select(MarketingCampaign)
        .where(and_(*conditions))
        .order_by(MarketingCampaign.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    campaigns = result.scalars().all()

    return [
        MarketingCampaignResponse(
            id=campaign.id,
            platform=campaign.platform,
            campaign_id=campaign.campaign_id,
            campaign_name=campaign.campaign_name,
            status=campaign.status,
            objective=campaign.objective,
            created_at=campaign.created_at,
        )
        for campaign in campaigns
    ]


@router.get("/ad-spend", response_model=List[AdSpendResponse])
async def get_ad_spend(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    platform: Optional[str] = Query(None),
    campaign_id: Optional[int] = Query(None),
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get ad spend data

    Returns daily ad spend data with impressions, clicks, conversions, and revenue.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    conditions = [
        AdSpend.date >= start_date,
        AdSpend.date <= end_date,
    ]

    # Join with campaign to get tenant_id
    query = (
        select(
            AdSpend,
            MarketingCampaign.campaign_name,
            MarketingCampaign.platform,
        )
        .join(MarketingCampaign, AdSpend.campaign_id == MarketingCampaign.id)
        .where(
            and_(
                MarketingCampaign.tenant_id == current_user.tenant_id,
                *conditions,
            )
        )
    )

    if platform:
        query = query.where(MarketingCampaign.platform == platform)

    if campaign_id:
        query = query.where(AdSpend.campaign_id == campaign_id)

    query = query.order_by(AdSpend.date.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.all()

    return [
        AdSpendResponse(
            id=row.AdSpend.id,
            campaign_id=row.AdSpend.campaign_id,
            campaign_name=row.campaign_name,
            platform=row.platform,
            date=row.AdSpend.date,
            spend=row.AdSpend.spend or Decimal("0"),
            impressions=row.AdSpend.impressions or 0,
            clicks=row.AdSpend.clicks or 0,
            conversions=row.AdSpend.conversions or 0,
            revenue=row.AdSpend.revenue or Decimal("0"),
            roas=row.AdSpend.roas or Decimal("0"),
            cpc=row.AdSpend.cpc or Decimal("0"),
            ctr=row.AdSpend.ctr or Decimal("0"),
            cpa=row.AdSpend.cpa or Decimal("0"),
        )
        for row in rows
    ]


@router.get("/campaign-performance", response_model=List[CampaignPerformance])
async def get_campaign_performance(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    platform: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get campaign performance summary

    Returns aggregated performance metrics for each campaign.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    conditions = [
        MarketingCampaign.tenant_id == current_user.tenant_id,
        AdSpend.date >= start_date,
        AdSpend.date <= end_date,
    ]

    if platform:
        conditions.append(MarketingCampaign.platform == platform)

    query = (
        select(
            MarketingCampaign.id,
            MarketingCampaign.campaign_name,
            MarketingCampaign.platform,
            func.sum(AdSpend.spend).label("total_spend"),
            func.sum(AdSpend.impressions).label("total_impressions"),
            func.sum(AdSpend.clicks).label("total_clicks"),
            func.sum(AdSpend.conversions).label("total_conversions"),
            func.sum(AdSpend.revenue).label("total_revenue"),
        )
        .join(AdSpend, AdSpend.campaign_id == MarketingCampaign.id)
        .where(and_(*conditions))
        .group_by(MarketingCampaign.id, MarketingCampaign.campaign_name, MarketingCampaign.platform)
        .order_by(desc("total_spend"))
    )

    result = await db.execute(query)
    campaigns = result.all()

    return [
        CampaignPerformance(
            campaign_id=c.id,
            campaign_name=c.campaign_name,
            platform=c.platform,
            total_spend=c.total_spend or Decimal("0"),
            total_impressions=c.total_impressions or 0,
            total_clicks=c.total_clicks or 0,
            total_conversions=c.total_conversions or 0,
            total_revenue=c.total_revenue or Decimal("0"),
            roas=(
                c.total_revenue / c.total_spend
                if c.total_spend and c.total_spend > 0
                else Decimal("0")
            ),
            avg_cpc=(
                c.total_spend / c.total_clicks
                if c.total_clicks and c.total_clicks > 0
                else Decimal("0")
            ),
            avg_ctr=(
                Decimal(c.total_clicks) / Decimal(c.total_impressions) * Decimal("100")
                if c.total_impressions and c.total_impressions > 0
                else Decimal("0")
            ),
            avg_cpa=(
                c.total_spend / c.total_conversions
                if c.total_conversions and c.total_conversions > 0
                else Decimal("0")
            ),
        )
        for c in campaigns
    ]


@router.get("/cac-ltv", response_model=CALTVMetrics)
async def get_cac_ltv_metrics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get CAC and LTV metrics

    Returns customer acquisition cost and lifetime value analysis.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=90)

    # Get marketing spend
    spend_query = (
        select(func.sum(AdSpend.spend))
        .join(MarketingCampaign, AdSpend.campaign_id == MarketingCampaign.id)
        .where(
            and_(
                MarketingCampaign.tenant_id == current_user.tenant_id,
                AdSpend.date >= start_date,
                AdSpend.date <= end_date,
            )
        )
    )
    spend_result = await db.execute(spend_query)
    total_spend = spend_result.scalar() or Decimal("0")

    # Get new customers (simplified - track via attribution in production)
    from app.models.order import Order

    customer_query = select(func.count(func.distinct(Order.customer_email))).where(
        and_(
            Order.tenant_id == current_user.tenant_id,
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
        )
    )
    customer_result = await db.execute(customer_query)
    new_customers = customer_result.scalar() or 0

    # Calculate CAC
    cac = total_spend / new_customers if new_customers > 0 else Decimal("0")

    # Calculate LTV (simplified - use 6 month average)
    revenue_query = select(
        func.avg(Order.total_amount)
    ).where(
        and_(
            Order.tenant_id == current_user.tenant_id,
            Order.created_at >= datetime.utcnow() - timedelta(days=180),
        )
    )
    revenue_result = await db.execute(revenue_query)
    avg_order_value = revenue_result.scalar() or Decimal("0")

    # Simplified LTV calculation (AOV * 3 orders assumption)
    avg_ltv = avg_order_value * Decimal("3")

    # LTV/CAC ratio
    ltv_cac_ratio = avg_ltv / cac if cac > 0 else Decimal("0")

    # Payback period (months)
    payback_period_days = int((cac / (avg_ltv / Decimal("180"))) if avg_ltv > 0 else 180)

    return CALTVMetrics(
        total_customers=new_customers,
        new_customers=new_customers,
        acquisition_cost=total_spend,
        cac=cac,
        avg_ltv=avg_ltv,
        ltv_cac_ratio=ltv_cac_ratio,
        payback_period_days=payback_period_days,
    )


@router.post("/sync/facebook")
async def sync_facebook_ads(
    sync_data: FacebookAdsSync,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync Facebook Ads data

    Triggers synchronization of Facebook Ads campaigns and spend data.
    """
    # This would call the Facebook Ads service to sync data
    # For now, return a pending status
    return {
        "message": "Facebook Ads sync initiated",
        "status": "pending",
        "ad_account_id": sync_data.ad_account_id,
        "date_range": {
            "start_date": sync_data.start_date.isoformat(),
            "end_date": sync_data.end_date.isoformat(),
        },
    }


@router.post("/sync/google")
async def sync_google_ads(
    sync_data: GoogleAdsSync,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync Google Ads data

    Triggers synchronization of Google Ads campaigns and spend data.
    """
    # This would call the Google Ads service to sync data
    # For now, return a pending status
    return {
        "message": "Google Ads sync initiated",
        "status": "pending",
        "customer_id": sync_data.customer_id,
        "date_range": {
            "start_date": sync_data.start_date.isoformat(),
            "end_date": sync_data.end_date.isoformat(),
        },
    }
