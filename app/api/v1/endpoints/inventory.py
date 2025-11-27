"""
Inventory endpoints
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from decimal import Decimal
from datetime import datetime, timedelta

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.inventory import InventorySnapshot, StockAlert
from app.models.product import Product, ProductVariant
from app.models.order import OrderItem, Order
from app.schemas.inventory import (
    InventorySnapshotResponse,
    StockAlertResponse,
    DeadStockAnalysis,
    SafetyStockCalculation,
    InventoryTurnoverAnalysis,
)
from app.schemas.analytics import SKUProfitability

router = APIRouter()


@router.get("/snapshots", response_model=List[InventorySnapshotResponse])
async def get_inventory_snapshots(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get inventory snapshots

    Returns current inventory levels with values.
    """
    query = (
        select(
            InventorySnapshot,
            Product.name,
            ProductVariant.sku,
        )
        .join(ProductVariant, InventorySnapshot.product_variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .where(InventorySnapshot.tenant_id == current_user.tenant_id)
        .order_by(InventorySnapshot.snapshot_date.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        InventorySnapshotResponse(
            id=row.InventorySnapshot.id,
            product_variant_id=row.InventorySnapshot.product_variant_id,
            product_name=row.name,
            sku=row.sku,
            quantity=row.InventorySnapshot.quantity,
            unit_cost=row.InventorySnapshot.unit_cost or Decimal("0"),
            total_value=row.InventorySnapshot.total_value or Decimal("0"),
            snapshot_date=row.InventorySnapshot.snapshot_date,
        )
        for row in rows
    ]


@router.get("/stock-alerts", response_model=List[StockAlertResponse])
async def get_stock_alerts(
    is_resolved: Optional[bool] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get stock alerts

    Returns stockout predictions and low stock alerts.
    """
    conditions = [StockAlert.tenant_id == current_user.tenant_id]

    if is_resolved is not None:
        conditions.append(StockAlert.is_resolved == is_resolved)

    if severity:
        conditions.append(StockAlert.severity == severity)

    query = (
        select(
            StockAlert,
            Product.name,
            ProductVariant.sku,
        )
        .join(ProductVariant, StockAlert.product_variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .where(and_(*conditions))
        .order_by(StockAlert.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        StockAlertResponse(
            id=row.StockAlert.id,
            product_variant_id=row.StockAlert.product_variant_id,
            product_name=row.name,
            sku=row.sku,
            alert_type=row.StockAlert.alert_type,
            current_stock=row.StockAlert.current_stock,
            predicted_stockout_date=row.StockAlert.predicted_stockout_date,
            days_until_stockout=row.StockAlert.days_until_stockout,
            recommended_reorder_qty=row.StockAlert.recommended_reorder_qty,
            severity=row.StockAlert.severity,
            is_resolved=row.StockAlert.is_resolved,
            created_at=row.StockAlert.created_at,
        )
        for row in rows
    ]


@router.get("/profitability", response_model=List[SKUProfitability])
async def get_sku_profitability(
    limit: int = Query(50, ge=1, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get SKU-level profitability

    Returns profit analysis for each SKU including revenue, costs, and margins.
    """
    # Get sales data with costs
    query = (
        select(
            Product.id,
            Product.name,
            ProductVariant.sku,
            ProductVariant.cost_price,
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(OrderItem, OrderItem.product_variant_id == ProductVariant.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            and_(
                Product.tenant_id == current_user.tenant_id,
                Order.created_at >= datetime.utcnow() - timedelta(days=90),
            )
        )
        .group_by(Product.id, Product.name, ProductVariant.sku, ProductVariant.cost_price)
        .order_by(desc("revenue"))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    products = result.all()

    profitability_data = []
    for p in products:
        revenue = p.revenue or Decimal("0")
        units_sold = p.units_sold or 0
        cost_price = p.cost_price or Decimal("0")

        # Calculate costs (simplified - enhance with actual data)
        cogs = cost_price * units_sold
        platform_fees = revenue * Decimal("0.02")  # 2% platform fee
        payment_gateway_fees = revenue * Decimal("0.02")  # 2% PG fee
        shipping_cost = units_sold * Decimal("50")  # ₹50 per shipment
        rto_cost = units_sold * Decimal("10")  # Estimated RTO cost
        marketing_cost = revenue * Decimal("0.10")  # 10% marketing

        net_profit = revenue - (
            cogs
            + platform_fees
            + payment_gateway_fees
            + shipping_cost
            + rto_cost
            + marketing_cost
        )

        profit_margin = (net_profit / revenue * 100) if revenue > 0 else Decimal("0")

        profitability_data.append(
            SKUProfitability(
                product_id=p.id,
                product_name=p.name,
                sku=p.sku,
                revenue=revenue,
                cogs=cogs,
                platform_fees=platform_fees,
                payment_gateway_fees=payment_gateway_fees,
                shipping_cost=shipping_cost,
                rto_cost=rto_cost,
                marketing_cost=marketing_cost,
                net_profit=net_profit,
                profit_margin=profit_margin,
                units_sold=units_sold,
            )
        )

    return profitability_data


@router.get("/dead-stock", response_model=List[DeadStockAnalysis])
async def get_dead_stock(
    limit: int = Query(100, ge=1, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get dead stock analysis

    Returns products with no sales in the last 90+ days.
    """
    # Get latest inventory
    latest_inventory = (
        select(
            InventorySnapshot.product_variant_id,
            InventorySnapshot.quantity,
            InventorySnapshot.unit_cost,
            InventorySnapshot.total_value,
        )
        .where(InventorySnapshot.tenant_id == current_user.tenant_id)
        .distinct(InventorySnapshot.product_variant_id)
        .order_by(InventorySnapshot.product_variant_id, InventorySnapshot.snapshot_date.desc())
    )

    # Get last sale date
    last_sale = (
        select(
            OrderItem.product_variant_id,
            func.max(Order.created_at).label("last_sale_date"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.tenant_id == current_user.tenant_id)
        .group_by(OrderItem.product_variant_id)
    )

    # Combine queries
    query = (
        select(
            Product.name,
            ProductVariant.id,
            ProductVariant.sku,
        )
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .where(
            and_(
                Product.tenant_id == current_user.tenant_id,
                ProductVariant.is_active == True,
            )
        )
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    variants = result.all()

    dead_stock_list = []
    for variant in variants:
        # Get last sale date for this variant
        sale_query = select(func.max(Order.created_at)).join(
            OrderItem, OrderItem.order_id == Order.id
        ).where(
            and_(
                OrderItem.product_variant_id == variant.id,
                Order.tenant_id == current_user.tenant_id,
            )
        )
        sale_result = await db.execute(sale_query)
        last_sale_date = sale_result.scalar()

        # Get current stock
        stock_query = (
            select(InventorySnapshot)
            .where(InventorySnapshot.product_variant_id == variant.id)
            .order_by(InventorySnapshot.snapshot_date.desc())
            .limit(1)
        )
        stock_result = await db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        if stock and stock.quantity > 0:
            days_since_sale = (
                (datetime.utcnow() - last_sale_date).days
                if last_sale_date
                else 999
            )

            if days_since_sale >= 30:  # Only include if no sales in last 30 days
                # Classify
                if days_since_sale >= 90:
                    classification = "Dead"
                    aging = "90+"
                elif days_since_sale >= 60:
                    classification = "Very Slow"
                    aging = "60-90"
                else:
                    classification = "Slow Moving"
                    aging = "30-60"

                # Calculate markdown
                markdown_pct = min(50, days_since_sale // 10)  # Up to 50% off
                unit_cost = stock.unit_cost or Decimal("0")
                recommended_clearance_price = unit_cost * (
                    Decimal("1") - Decimal(markdown_pct) / Decimal("100")
                )

                dead_stock_list.append(
                    DeadStockAnalysis(
                        product_variant_id=variant.id,
                        product_name=variant.name,
                        sku=variant.sku,
                        current_stock=stock.quantity,
                        days_since_last_sale=days_since_sale,
                        stock_value=stock.total_value or Decimal("0"),
                        classification=classification,
                        aging_bracket=aging,
                        recommended_markdown=Decimal(markdown_pct),
                        recommended_clearance_price=recommended_clearance_price,
                    )
                )

    return dead_stock_list[:limit]


@router.get("/turnover-analysis", response_model=List[InventoryTurnoverAnalysis])
async def get_inventory_turnover(
    limit: int = Query(50, ge=1, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get inventory turnover analysis

    Returns inventory turnover ratios and days of inventory for each SKU.
    """
    # This is a simplified implementation
    # For production, you'd calculate actual COGS and average inventory values

    query = (
        select(
            Product.id,
            Product.name,
            ProductVariant.id.label("variant_id"),
            ProductVariant.sku,
            ProductVariant.cost_price,
        )
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .where(
            and_(
                Product.tenant_id == current_user.tenant_id,
                ProductVariant.is_active == True,
            )
        )
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    products = result.all()

    turnover_analysis = []
    for p in products:
        # Simplified calculations - enhance with actual data
        avg_inventory_value = Decimal("10000")  # Placeholder
        cogs = Decimal("40000")  # Placeholder for annual COGS

        inventory_turnover_ratio = (
            cogs / avg_inventory_value if avg_inventory_value > 0 else Decimal("0")
        )
        days_of_inventory = (
            Decimal("365") / inventory_turnover_ratio
            if inventory_turnover_ratio > 0
            else Decimal("365")
        )

        # Performance rating
        if inventory_turnover_ratio >= 8:
            performance = "Excellent"
        elif inventory_turnover_ratio >= 4:
            performance = "Good"
        elif inventory_turnover_ratio >= 2:
            performance = "Average"
        else:
            performance = "Poor"

        turnover_analysis.append(
            InventoryTurnoverAnalysis(
                product_variant_id=p.variant_id,
                product_name=p.name,
                sku=p.sku,
                avg_inventory_value=avg_inventory_value,
                cogs=cogs,
                inventory_turnover_ratio=inventory_turnover_ratio,
                days_of_inventory=days_of_inventory,
                performance_rating=performance,
            )
        )

    return turnover_analysis
