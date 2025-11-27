"""
Analytics endpoints
"""
from fastapi import APIRouter, Depends, Query
from datetime import date, timedelta
from typing import List, Optional

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    DashboardMetrics,
    RevenueDataPoint,
    ChannelPerformance,
    ProductPerformance,
    StateRevenue,
    PaymentMethodDistribution,
    OrderStatusDistribution,
    DailyMetricsResponse,
    PinCodeMetricsResponse,
    CODRTOAnalytics,
    InventoryAnalytics,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard overview metrics

    Returns key metrics like revenue, orders, AOV, profit margin, RTO rate, etc.
    with comparison to previous period.
    """
    # Default to last 30 days if not specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_dashboard_metrics(start_date, end_date)


@router.get("/revenue-trend", response_model=List[RevenueDataPoint])
async def get_revenue_trend(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get revenue trend over time

    Returns daily revenue and order count data points for charting.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_revenue_trend(start_date, end_date)


@router.get("/channel-performance", response_model=List[ChannelPerformance])
async def get_channel_performance(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get channel-wise performance metrics

    Returns revenue and order breakdown by sales channel.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_channel_performance(start_date, end_date)


@router.get("/top-products", response_model=List[ProductPerformance])
async def get_top_products(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get top selling products

    Returns the top N products by revenue.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_top_products(start_date, end_date, limit)


@router.get("/state-revenue", response_model=List[StateRevenue])
async def get_state_revenue(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get state-wise revenue breakdown

    Returns revenue and orders by Indian state.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_state_revenue(start_date, end_date)


@router.get(
    "/payment-method-distribution", response_model=List[PaymentMethodDistribution]
)
async def get_payment_method_distribution(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get payment method distribution

    Returns breakdown of orders by payment method (COD, Prepaid, etc.).
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_payment_method_distribution(start_date, end_date)


@router.get("/order-status-distribution", response_model=List[OrderStatusDistribution])
async def get_order_status_distribution(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get order status distribution

    Returns breakdown of orders by status (pending, confirmed, shipped, etc.).
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_order_status_distribution(start_date, end_date)


@router.get("/daily-metrics", response_model=List[DailyMetricsResponse])
async def get_daily_metrics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily aggregated metrics

    Returns comprehensive daily metrics including orders, revenue, RTO, profitability, etc.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_daily_metrics(start_date, end_date)


@router.get("/pincode-metrics", response_model=List[PinCodeMetricsResponse])
async def get_pincode_metrics(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    risk_level: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pin code performance metrics

    Returns pin code-wise analytics including RTO rates, risk scores, delivery performance, etc.
    Can be filtered by risk level and state.
    """
    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_pincode_metrics(
        limit=limit, offset=offset, risk_level=risk_level, state=state
    )


@router.get("/cod-rto-analytics", response_model=CODRTOAnalytics)
async def get_cod_rto_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get COD/RTO analytics

    Returns comprehensive RTO analytics including breakdown by channel, courier, pin code risk, and NDR metrics.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_cod_rto_analytics(start_date, end_date)


@router.get("/inventory-analytics", response_model=InventoryAnalytics)
async def get_inventory_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get inventory analytics

    Returns comprehensive inventory metrics including value, DOI, turnover, stockouts, and dead stock.
    """
    service = AnalyticsService(db, current_user.tenant_id)
    return await service.get_inventory_analytics()
