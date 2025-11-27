"""
Subscriptions endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPlan, Invoice
from app.models.tenant import Tenant
from app.services.razorpay_service import RazorpayService
from app.schemas.subscription import (
    SubscriptionPlanResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUsage,
    InvoiceResponse,
    SubscriptionCancel,
)

router = APIRouter()


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    """
    List all subscription plans

    Returns available subscription plans (Trial, Starter, Growth, Professional).
    """
    query = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
    result = await db.execute(query)
    plans = result.scalars().all()

    return [
        SubscriptionPlanResponse(
            id=plan.id,
            name=plan.name,
            slug=plan.slug,
            price=plan.price or 0,
            billing_period=plan.billing_period,
            max_channels=plan.max_channels,
            max_orders=plan.max_orders,
            features=plan.features or {},
            is_active=plan.is_active,
        )
        for plan in plans
    ]


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current subscription

    Returns the tenant's active subscription details.
    """
    query = (
        select(Subscription, SubscriptionPlan)
        .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id)
        .where(
            and_(
                Subscription.tenant_id == current_user.tenant_id,
                Subscription.status.in_(["active", "trialing"]),
            )
        )
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="No active subscription found")

    subscription, plan = row

    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        plan_id=subscription.plan_id,
        plan_name=plan.name,
        razorpay_subscription_id=subscription.razorpay_subscription_id,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        created_at=subscription.created_at,
    )


@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new subscription

    Subscribes to a plan using Razorpay payment integration.
    """
    # Get tenant
    tenant_query = select(Tenant).where(Tenant.id == current_user.tenant_id)
    tenant_result = await db.execute(tenant_query)
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get plan
    plan_query = select(SubscriptionPlan).where(
        SubscriptionPlan.id == subscription_data.plan_id
    )
    plan_result = await db.execute(plan_query)
    plan = plan_result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Create Razorpay subscription
    razorpay_service = RazorpayService(db, current_user.tenant_id)

    try:
        razorpay_subscription = await razorpay_service.create_subscription(
            plan_id=plan.id,
            customer_email=current_user.email,
            customer_name=current_user.full_name,
        )

        subscription = Subscription(
            tenant_id=current_user.tenant_id,
            plan_id=plan.id,
            razorpay_subscription_id=razorpay_subscription.get("id"),
            status="active",
            cancel_at_period_end=False,
        )

        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

        return SubscriptionResponse(
            id=subscription.id,
            tenant_id=subscription.tenant_id,
            plan_id=subscription.plan_id,
            plan_name=plan.name,
            razorpay_subscription_id=subscription.razorpay_subscription_id,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            created_at=subscription.created_at,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Subscription creation failed: {str(e)}")


@router.get("/usage", response_model=SubscriptionUsage)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get subscription usage

    Returns current usage vs plan limits for channels and orders.
    """
    # Get active subscription
    sub_query = (
        select(Subscription, SubscriptionPlan)
        .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id)
        .where(
            and_(
                Subscription.tenant_id == current_user.tenant_id,
                Subscription.status.in_(["active", "trialing"]),
            )
        )
    )

    sub_result = await db.execute(sub_query)
    row = sub_result.first()

    if not row:
        raise HTTPException(status_code=404, detail="No active subscription found")

    subscription, plan = row

    # Get channel count
    from app.models.channel import Channel

    channel_query = select(func.count(Channel.id)).where(
        Channel.tenant_id == current_user.tenant_id
    )
    channel_result = await db.execute(channel_query)
    channel_count = channel_result.scalar() or 0

    # Get order count for current month (simplified)
    from app.models.order import Order
    from datetime import datetime, timedelta
    from sqlalchemy import func

    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)

    order_query = select(func.count(Order.id)).where(
        and_(
            Order.tenant_id == current_user.tenant_id,
            Order.created_at >= start_of_month,
        )
    )
    order_result = await db.execute(order_query)
    order_count = order_result.scalar() or 0

    # Calculate usage
    max_orders = plan.max_orders or 999999
    usage_percentage = (order_count / max_orders * 100) if max_orders > 0 else 0

    return SubscriptionUsage(
        plan_name=plan.name,
        max_channels=plan.max_channels,
        current_channels=channel_count,
        max_orders=plan.max_orders,
        current_orders=order_count,
        usage_percentage=usage_percentage,
        is_overaged=order_count > max_orders,
        overage_amount=max(0, order_count - max_orders),
    )


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    cancel_data: SubscriptionCancel,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel subscription

    Cancels the current subscription (optionally at period end).
    """
    # Get active subscription
    sub_query = (
        select(Subscription, SubscriptionPlan)
        .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id)
        .where(
            and_(
                Subscription.tenant_id == current_user.tenant_id,
                Subscription.status.in_(["active", "trialing"]),
            )
        )
    )

    sub_result = await db.execute(sub_query)
    row = sub_result.first()

    if not row:
        raise HTTPException(status_code=404, detail="No active subscription found")

    subscription, plan = row

    if cancel_data.cancel_at_period_end:
        subscription.cancel_at_period_end = True
    else:
        subscription.status = "cancelled"

    await db.commit()
    await db.refresh(subscription)

    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        plan_id=subscription.plan_id,
        plan_name=plan.name,
        razorpay_subscription_id=subscription.razorpay_subscription_id,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        created_at=subscription.created_at,
    )


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List invoices

    Returns billing invoices for the tenant's subscription.
    """
    # Get subscription
    sub_query = select(Subscription.id).where(
        Subscription.tenant_id == current_user.tenant_id
    )
    sub_result = await db.execute(sub_query)
    subscription_ids = [row[0] for row in sub_result.all()]

    if not subscription_ids:
        return []

    # Get invoices
    invoice_query = (
        select(Invoice)
        .where(Invoice.subscription_id.in_(subscription_ids))
        .order_by(Invoice.invoice_date.desc())
        .limit(limit)
        .offset(offset)
    )

    invoice_result = await db.execute(invoice_query)
    invoices = invoice_result.scalars().all()

    return [
        InvoiceResponse(
            id=invoice.id,
            subscription_id=invoice.subscription_id,
            invoice_number=invoice.invoice_number,
            razorpay_invoice_id=invoice.razorpay_invoice_id,
            amount=invoice.amount or 0,
            tax=invoice.tax or 0,
            total=invoice.total or 0,
            status=invoice.status,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            paid_at=invoice.paid_at,
            invoice_url=invoice.invoice_url,
        )
        for invoice in invoices
    ]
