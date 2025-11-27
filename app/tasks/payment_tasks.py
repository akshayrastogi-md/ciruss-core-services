"""
Payment tasks for Celery
"""
from app.tasks.celery_app import celery_app
from datetime import datetime, timedelta
from decimal import Decimal


@celery_app.task(name="app.tasks.payment_tasks.track_cod_remittances")
def track_cod_remittances(tenant_id: int):
    """
    Track COD remittances from channels

    Runs daily at 10 AM to track pending COD remittances.
    """
    from app.db.session import get_sync_db
    from app.models.payment import CODRemittance
    from app.models.order import Order, OrderStatus
    from app.models.channel import Channel
    from sqlalchemy import select, and_, func

    db = next(get_sync_db())

    try:
        # Get all COD orders that are delivered but not remitted
        channels = db.execute(
            select(Channel).where(Channel.tenant_id == tenant_id)
        ).scalars().all()

        remittances_tracked = 0

        for channel in channels:
            # Settlement cycles
            settlement_days = {
                "shopify": 2,
                "woocommerce": 7,
                "amazon": 7,
                "flipkart": 14,
            }.get(channel.channel_type, 7)

            cutoff_date = datetime.utcnow() - timedelta(days=settlement_days)

            # Get delivered COD orders
            orders = db.execute(
                select(Order).where(
                    and_(
                        Order.channel_id == channel.id,
                        Order.payment_method == "COD",
                        Order.status == OrderStatus.DELIVERED,
                        Order.created_at <= cutoff_date,
                    )
                )
            ).scalars().all()

            for order in orders:
                # Check if remittance exists
                existing = db.execute(
                    select(CODRemittance).where(CODRemittance.order_id == order.id)
                ).scalar_one_or_none()

                if not existing:
                    # Create remittance record
                    remittance = CODRemittance(
                        tenant_id=tenant_id,
                        order_id=order.id,
                        channel_id=channel.id,
                        amount=order.total_amount or Decimal("0"),
                        expected_remittance_date=order.created_at + timedelta(days=settlement_days),
                        status="pending",
                    )
                    db.add(remittance)
                    remittances_tracked += 1

        db.commit()

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "remittances_tracked": remittances_tracked,
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
