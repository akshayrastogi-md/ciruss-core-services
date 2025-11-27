"""
Subscription tasks for Celery
"""
from app.tasks.celery_app import celery_app
from datetime import datetime, timedelta
from decimal import Decimal


@celery_app.task(name="app.tasks.subscription_tasks.check_subscription_usage")
def check_subscription_usage(tenant_id: int):
    """
    Check subscription usage and send alerts if approaching limits

    Runs hourly to check usage against plan limits.
    """
    from app.db.session import get_sync_db
    from app.models.subscription import Subscription, SubscriptionPlan
    from app.models.order import Order
    from app.models.channel import Channel
    from sqlalchemy import select, and_, func

    db = next(get_sync_db())

    try:
        # Get active subscription
        subscription = db.execute(
            select(Subscription, SubscriptionPlan)
            .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id)
            .where(
                and_(
                    Subscription.tenant_id == tenant_id,
                    Subscription.status.in_(["active", "trialing"]),
                )
            )
        ).first()

        if not subscription:
            return {"status": "skipped", "reason": "No active subscription"}

        sub, plan = subscription

        # Get current month order count
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)

        order_count = db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.created_at >= start_of_month,
                )
            )
        ).scalar() or 0

        # Get channel count
        channel_count = db.execute(
            select(func.count(Channel.id)).where(Channel.tenant_id == tenant_id)
        ).scalar() or 0

        # Check limits
        max_orders = plan.max_orders or 999999
        max_channels = plan.max_channels or 999

        alerts = []

        # Order usage
        order_usage_pct = (order_count / max_orders * 100) if max_orders > 0 else 0

        if order_usage_pct >= 80:
            alerts.append({
                "type": "order_limit",
                "usage_percentage": order_usage_pct,
                "current": order_count,
                "limit": max_orders,
            })

        # Channel usage
        if channel_count >= max_channels:
            alerts.append({
                "type": "channel_limit",
                "current": channel_count,
                "limit": max_channels,
            })

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "plan": plan.name,
            "order_usage": {
                "current": order_count,
                "limit": max_orders,
                "percentage": float(order_usage_pct),
            },
            "channel_usage": {
                "current": channel_count,
                "limit": max_channels,
            },
            "alerts": alerts,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
