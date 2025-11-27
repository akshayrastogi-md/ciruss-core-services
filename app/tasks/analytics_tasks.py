"""
Analytics tasks for Celery
"""
from app.tasks.celery_app import celery_app
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, and_
from decimal import Decimal


@celery_app.task(name="app.tasks.analytics_tasks.aggregate_daily_metrics")
def aggregate_daily_metrics(tenant_id: int, target_date: str = None):
    """
    Aggregate daily metrics for a tenant

    Runs daily at 1 AM to aggregate previous day's metrics.
    """
    from app.db.session import get_sync_db
    from app.models.analytics import DailyMetrics
    from app.models.order import Order, OrderStatus

    db = next(get_sync_db())

    # Parse date
    if target_date:
        metrics_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        metrics_date = date.today() - timedelta(days=1)

    start_datetime = datetime.combine(metrics_date, datetime.min.time())
    end_datetime = datetime.combine(metrics_date, datetime.max.time())

    try:
        # Get orders for the day
        orders = db.execute(
            select(Order).where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.created_at >= start_datetime,
                    Order.created_at <= end_datetime,
                )
            )
        ).scalars().all()

        # Calculate metrics
        total_orders = len(orders)
        total_revenue = sum(order.total_amount or Decimal("0") for order in orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else Decimal("0")

        cod_orders = sum(1 for order in orders if order.payment_method == "COD")
        prepaid_orders = total_orders - cod_orders
        cod_percentage = (cod_orders / total_orders * 100) if total_orders > 0 else Decimal("0")

        confirmed_orders = sum(1 for order in orders if order.status == OrderStatus.CONFIRMED)
        shipped_orders = sum(1 for order in orders if order.status == OrderStatus.SHIPPED)
        delivered_orders = sum(1 for order in orders if order.status == OrderStatus.DELIVERED)
        cancelled_orders = sum(1 for order in orders if order.status == OrderStatus.CANCELLED)
        rto_orders = sum(1 for order in orders if order.status == OrderStatus.RTO)

        rto_rate = (rto_orders / total_orders * 100) if total_orders > 0 else Decimal("0")

        # Check if metrics already exist
        existing = db.execute(
            select(DailyMetrics).where(
                and_(
                    DailyMetrics.tenant_id == tenant_id,
                    DailyMetrics.date == metrics_date,
                )
            )
        ).scalar_one_or_none()

        if existing:
            # Update existing
            existing.total_orders = total_orders
            existing.total_revenue = total_revenue
            existing.avg_order_value = avg_order_value
            existing.cod_orders = cod_orders
            existing.prepaid_orders = prepaid_orders
            existing.cod_percentage = cod_percentage
            existing.confirmed_orders = confirmed_orders
            existing.shipped_orders = shipped_orders
            existing.delivered_orders = delivered_orders
            existing.cancelled_orders = cancelled_orders
            existing.rto_orders = rto_orders
            existing.rto_rate = rto_rate
        else:
            # Create new
            metrics = DailyMetrics(
                tenant_id=tenant_id,
                date=metrics_date,
                total_orders=total_orders,
                total_revenue=total_revenue,
                avg_order_value=avg_order_value,
                cod_orders=cod_orders,
                prepaid_orders=prepaid_orders,
                cod_percentage=cod_percentage,
                confirmed_orders=confirmed_orders,
                shipped_orders=shipped_orders,
                delivered_orders=delivered_orders,
                cancelled_orders=cancelled_orders,
                rto_orders=rto_orders,
                rto_rate=rto_rate,
            )
            db.add(metrics)

        db.commit()

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "date": metrics_date.isoformat(),
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.analytics_tasks.update_pincode_metrics")
def update_pincode_metrics(tenant_id: int):
    """
    Update pin code metrics

    Runs daily at 3 AM to update pin code risk scores and performance.
    """
    from app.db.session import get_sync_db
    from app.models.analytics import PinCodeMetrics
    from app.models.order import Order, OrderStatus

    db = next(get_sync_db())

    try:
        # Get all orders with pincodes
        orders_query = select(
            Order.shipping_pincode,
            func.count(Order.id).label("total_orders"),
            func.sum(func.case((Order.status == OrderStatus.DELIVERED, 1), else_=0)).label("delivered"),
            func.sum(func.case((Order.status == OrderStatus.RTO, 1), else_=0)).label("rto"),
            func.sum(func.case((Order.payment_method == "COD", 1), else_=0)).label("cod"),
            func.avg(Order.total_amount).label("avg_order_value"),
        ).where(
            and_(
                Order.tenant_id == tenant_id,
                Order.shipping_pincode.isnot(None),
            )
        ).group_by(Order.shipping_pincode)

        results = db.execute(orders_query).all()

        for row in results:
            pincode = row.shipping_pincode
            total_orders = row.total_orders or 0
            delivered = row.delivered or 0
            rto = row.rto or 0
            cod = row.cod or 0

            rto_rate = (rto / total_orders * 100) if total_orders > 0 else Decimal("0")

            # Calculate risk score (0-100)
            risk_score = min(100, int(rto_rate * 2))  # Simplified

            # Determine risk level
            if risk_score >= 70:
                risk_level = "High"
            elif risk_score >= 40:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            # Update or create
            existing = db.execute(
                select(PinCodeMetrics).where(
                    and_(
                        PinCodeMetrics.tenant_id == tenant_id,
                        PinCodeMetrics.pincode == pincode,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                existing.total_orders = total_orders
                existing.delivered_orders = delivered
                existing.rto_orders = rto
                existing.rto_rate = rto_rate
                existing.cod_orders = cod
                existing.risk_score = risk_score
                existing.risk_level = risk_level
                existing.avg_order_value = row.avg_order_value or Decimal("0")
            else:
                metrics = PinCodeMetrics(
                    tenant_id=tenant_id,
                    pincode=pincode,
                    total_orders=total_orders,
                    delivered_orders=delivered,
                    rto_orders=rto,
                    rto_rate=rto_rate,
                    cod_orders=cod,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    avg_order_value=row.avg_order_value or Decimal("0"),
                )
                db.add(metrics)

        db.commit()

        return {"status": "success", "tenant_id": tenant_id, "pincodes_updated": len(results)}

    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
