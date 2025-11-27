"""
Inventory tasks for Celery
"""
from app.tasks.celery_app import celery_app
from datetime import datetime, timedelta, date
from decimal import Decimal


@celery_app.task(name="app.tasks.inventory_tasks.create_inventory_snapshot")
def create_inventory_snapshot(tenant_id: int):
    """
    Create daily inventory snapshot

    Runs daily at 4 AM to snapshot inventory levels.
    """
    from app.db.session import get_sync_db
    from app.models.inventory import InventorySnapshot
    from app.models.product import ProductVariant
    from sqlalchemy import select, and_

    db = next(get_sync_db())

    try:
        # Get all active product variants
        variants = db.execute(
            select(ProductVariant).where(
                and_(
                    ProductVariant.tenant_id == tenant_id,
                    ProductVariant.is_active == True,
                )
            )
        ).scalars().all()

        snapshot_date = datetime.utcnow()
        snapshots_created = 0

        for variant in variants:
            snapshot = InventorySnapshot(
                tenant_id=tenant_id,
                product_variant_id=variant.id,
                quantity=variant.stock_quantity or 0,
                unit_cost=variant.cost_price or Decimal("0"),
                total_value=(variant.stock_quantity or 0) * (variant.cost_price or Decimal("0")),
                snapshot_date=snapshot_date,
            )
            db.add(snapshot)
            snapshots_created += 1

        db.commit()

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "snapshots_created": snapshots_created,
            "date": snapshot_date.isoformat(),
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.inventory_tasks.generate_stock_alerts")
def generate_stock_alerts(tenant_id: int):
    """
    Generate stock alerts

    Runs every 6 hours to check for low stock and stockout predictions.
    """
    from app.db.session import get_sync_db
    from app.models.inventory import StockAlert
    from app.models.product import ProductVariant, Product
    from app.models.order import OrderItem, Order
    from sqlalchemy import select, and_, func
    from datetime import timedelta

    db = next(get_sync_db())

    try:
        # Get all active product variants
        variants = db.execute(
            select(ProductVariant, Product)
            .join(Product, ProductVariant.product_id == Product.id)
            .where(
                and_(
                    ProductVariant.tenant_id == tenant_id,
                    ProductVariant.is_active == True,
                )
            )
        ).all()

        alerts_created = 0

        for variant, product in variants:
            current_stock = variant.stock_quantity or 0

            # Calculate daily demand (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            demand_query = (
                select(func.sum(OrderItem.quantity))
                .join(Order, Order.id == OrderItem.order_id)
                .where(
                    and_(
                        OrderItem.product_variant_id == variant.id,
                        Order.created_at >= thirty_days_ago,
                    )
                )
            )

            total_demand = db.execute(demand_query).scalar() or 0
            daily_demand = total_demand / 30 if total_demand > 0 else 0

            # Predict stockout
            if daily_demand > 0:
                days_until_stockout = int(current_stock / daily_demand)
                predicted_stockout_date = date.today() + timedelta(days=days_until_stockout)

                # Determine severity
                if days_until_stockout <= 7:
                    severity = "Critical"
                elif days_until_stockout <= 14:
                    severity = "High"
                elif days_until_stockout <= 30:
                    severity = "Medium"
                else:
                    severity = None

                if severity:
                    # Check if alert already exists
                    existing = db.execute(
                        select(StockAlert).where(
                            and_(
                                StockAlert.product_variant_id == variant.id,
                                StockAlert.is_resolved == False,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        alert = StockAlert(
                            tenant_id=tenant_id,
                            product_variant_id=variant.id,
                            alert_type="stockout_prediction",
                            current_stock=current_stock,
                            predicted_stockout_date=predicted_stockout_date,
                            days_until_stockout=days_until_stockout,
                            recommended_reorder_qty=int(daily_demand * 30),  # 30 days worth
                            severity=severity,
                            is_resolved=False,
                        )
                        db.add(alert)
                        alerts_created += 1

        db.commit()

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "alerts_created": alerts_created,
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
