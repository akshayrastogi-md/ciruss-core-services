"""
Analytics service
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, case
from decimal import Decimal

from app.models.analytics import DailyMetrics, PinCodeMetrics
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import ProductVariant, Product
from app.models.channel import Channel
from app.models.shipment import Shipment, ShipmentStatus
from app.models.marketing import AdSpend, MarketingCampaign
from app.models.payment import CODRemittance, PaymentReconciliation
from app.models.inventory import StockAlert, InventorySnapshot
from app.schemas.analytics import (
    DashboardMetrics,
    RevenueDataPoint,
    ChannelPerformance,
    ProductPerformance,
    StateRevenue,
    PaymentMethodDistribution,
    OrderStatusDistribution,
    CustomerMetrics,
    MarketingMetrics,
    ChannelMarketingPerformance,
    DailyMetricsResponse,
    PinCodeMetricsResponse,
    CODRTOAnalytics,
    InventoryAnalytics,
    SKUProfitability,
    WorkingCapitalMetrics,
)


class AnalyticsService:
    """Analytics service"""

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_dashboard_metrics(
        self, start_date: date, end_date: date
    ) -> DashboardMetrics:
        """Get dashboard overview metrics"""

        # Get current period metrics
        current_query = select(
            func.sum(DailyMetrics.total_revenue).label("total_revenue"),
            func.sum(DailyMetrics.total_orders).label("total_orders"),
            func.avg(DailyMetrics.avg_order_value).label("avg_order_value"),
            func.avg(DailyMetrics.profit_margin).label("profit_margin"),
            func.avg(DailyMetrics.rto_rate).label("rto_rate"),
            func.avg(DailyMetrics.cod_percentage).label("cod_percentage"),
            func.sum(DailyMetrics.marketing_spend).label("marketing_spend"),
            func.sum(DailyMetrics.marketing_revenue).label("marketing_revenue"),
        ).where(
            and_(
                DailyMetrics.tenant_id == self.tenant_id,
                DailyMetrics.date >= start_date,
                DailyMetrics.date <= end_date,
            )
        )

        result = await self.db.execute(current_query)
        current_data = result.first()

        # Calculate previous period for comparison
        period_days = (end_date - start_date).days + 1
        prev_start = start_date - timedelta(days=period_days)
        prev_end = start_date - timedelta(days=1)

        prev_query = select(
            func.sum(DailyMetrics.total_revenue).label("prev_revenue"),
            func.sum(DailyMetrics.total_orders).label("prev_orders"),
            func.avg(DailyMetrics.avg_order_value).label("prev_aov"),
        ).where(
            and_(
                DailyMetrics.tenant_id == self.tenant_id,
                DailyMetrics.date >= prev_start,
                DailyMetrics.date <= prev_end,
            )
        )

        prev_result = await self.db.execute(prev_query)
        prev_data = prev_result.first()

        # Count active SKUs
        sku_query = select(func.count(ProductVariant.id)).where(
            and_(
                ProductVariant.tenant_id == self.tenant_id,
                ProductVariant.is_active == True,
            )
        )
        sku_result = await self.db.execute(sku_query)
        active_skus = sku_result.scalar() or 0

        # Calculate metrics
        total_revenue = current_data.total_revenue or Decimal("0")
        total_orders = current_data.total_orders or 0
        avg_order_value = current_data.avg_order_value or Decimal("0")
        profit_margin = current_data.profit_margin or Decimal("0")
        rto_rate = current_data.rto_rate or Decimal("0")
        cod_percentage = current_data.cod_percentage or Decimal("0")
        marketing_spend = current_data.marketing_spend or Decimal("0")
        marketing_revenue = current_data.marketing_revenue or Decimal("0")

        # Calculate ROAS
        roas = (
            marketing_revenue / marketing_spend
            if marketing_spend > 0
            else Decimal("0")
        )

        # Calculate changes
        prev_revenue = prev_data.prev_revenue or Decimal("1")
        prev_orders = prev_data.prev_orders or 1
        prev_aov = prev_data.prev_aov or Decimal("1")

        revenue_change = (
            ((total_revenue - prev_revenue) / prev_revenue * 100)
            if prev_revenue > 0
            else Decimal("0")
        )
        orders_change = (
            ((total_orders - prev_orders) / prev_orders * 100)
            if prev_orders > 0
            else Decimal("0")
        )
        aov_change = (
            ((avg_order_value - prev_aov) / prev_aov * 100)
            if prev_aov > 0
            else Decimal("0")
        )

        return DashboardMetrics(
            total_revenue=total_revenue,
            total_orders=total_orders,
            average_order_value=avg_order_value,
            profit_margin=profit_margin,
            rto_rate=rto_rate,
            cod_percentage=cod_percentage,
            active_skus=active_skus,
            marketing_spend=marketing_spend,
            roas=roas,
            revenue_change=revenue_change,
            orders_change=orders_change,
            aov_change=aov_change,
        )

    async def get_revenue_trend(
        self, start_date: date, end_date: date
    ) -> List[RevenueDataPoint]:
        """Get revenue trend data"""

        query = (
            select(
                DailyMetrics.date,
                DailyMetrics.total_revenue,
                DailyMetrics.total_orders,
            )
            .where(
                and_(
                    DailyMetrics.tenant_id == self.tenant_id,
                    DailyMetrics.date >= start_date,
                    DailyMetrics.date <= end_date,
                )
            )
            .order_by(DailyMetrics.date)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            RevenueDataPoint(
                date=row.date,
                revenue=row.total_revenue or Decimal("0"),
                orders=row.total_orders or 0,
            )
            for row in rows
        ]

    async def get_channel_performance(
        self, start_date: date, end_date: date
    ) -> List[ChannelPerformance]:
        """Get channel-wise performance"""

        query = (
            select(
                Channel.id,
                Channel.name,
                Channel.channel_type,
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("orders"),
            )
            .join(Order, Order.channel_id == Channel.id)
            .where(
                and_(
                    Channel.tenant_id == self.tenant_id,
                    Order.created_at >= datetime.combine(
                        start_date, datetime.min.time()
                    ),
                    Order.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .group_by(Channel.id, Channel.name, Channel.channel_type)
            .order_by(desc("revenue"))
        )

        result = await self.db.execute(query)
        rows = result.all()

        # Calculate total for percentage
        total_revenue = sum(row.revenue or Decimal("0") for row in rows)

        return [
            ChannelPerformance(
                channel_id=row.id,
                channel_name=row.name,
                channel_type=row.channel_type,
                revenue=row.revenue or Decimal("0"),
                orders=row.orders or 0,
                percentage=(
                    (row.revenue / total_revenue * 100)
                    if total_revenue > 0
                    else Decimal("0")
                ),
            )
            for row in rows
        ]

    async def get_top_products(
        self, start_date: date, end_date: date, limit: int = 10
    ) -> List[ProductPerformance]:
        """Get top selling products"""

        query = (
            select(
                Product.id,
                Product.name,
                ProductVariant.sku,
                func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
                func.sum(OrderItem.quantity).label("quantity_sold"),
            )
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .join(OrderItem, OrderItem.product_variant_id == ProductVariant.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                and_(
                    Product.tenant_id == self.tenant_id,
                    Order.created_at >= datetime.combine(
                        start_date, datetime.min.time()
                    ),
                    Order.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .group_by(Product.id, Product.name, ProductVariant.sku)
            .order_by(desc("revenue"))
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            ProductPerformance(
                product_id=row.id,
                product_name=row.name,
                sku=row.sku,
                revenue=row.revenue or Decimal("0"),
                quantity_sold=row.quantity_sold or 0,
            )
            for row in rows
        ]

    async def get_state_revenue(
        self, start_date: date, end_date: date
    ) -> List[StateRevenue]:
        """Get state-wise revenue breakdown"""

        query = (
            select(
                Order.billing_state,
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("orders"),
            )
            .where(
                and_(
                    Order.tenant_id == self.tenant_id,
                    Order.created_at >= datetime.combine(
                        start_date, datetime.min.time()
                    ),
                    Order.created_at <= datetime.combine(end_date, datetime.max.time()),
                    Order.billing_state.isnot(None),
                )
            )
            .group_by(Order.billing_state)
            .order_by(desc("revenue"))
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            StateRevenue(
                state=row.billing_state,
                revenue=row.revenue or Decimal("0"),
                orders=row.orders or 0,
            )
            for row in rows
        ]

    async def get_payment_method_distribution(
        self, start_date: date, end_date: date
    ) -> List[PaymentMethodDistribution]:
        """Get payment method distribution"""

        query = (
            select(
                Order.payment_method,
                func.count(Order.id).label("count"),
            )
            .where(
                and_(
                    Order.tenant_id == self.tenant_id,
                    Order.created_at >= datetime.combine(
                        start_date, datetime.min.time()
                    ),
                    Order.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .group_by(Order.payment_method)
        )

        result = await self.db.execute(query)
        rows = result.all()

        total_count = sum(row.count for row in rows)

        return [
            PaymentMethodDistribution(
                method=row.payment_method or "Unknown",
                count=row.count,
                percentage=(
                    (row.count / total_count * 100) if total_count > 0 else Decimal("0")
                ),
            )
            for row in rows
        ]

    async def get_order_status_distribution(
        self, start_date: date, end_date: date
    ) -> List[OrderStatusDistribution]:
        """Get order status distribution"""

        query = (
            select(
                Order.status,
                func.count(Order.id).label("count"),
            )
            .where(
                and_(
                    Order.tenant_id == self.tenant_id,
                    Order.created_at >= datetime.combine(
                        start_date, datetime.min.time()
                    ),
                    Order.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .group_by(Order.status)
        )

        result = await self.db.execute(query)
        rows = result.all()

        total_count = sum(row.count for row in rows)

        return [
            OrderStatusDistribution(
                status=row.status.value if hasattr(row.status, "value") else row.status,
                count=row.count,
                percentage=(
                    (row.count / total_count * 100) if total_count > 0 else Decimal("0")
                ),
            )
            for row in rows
        ]

    async def get_daily_metrics(
        self, start_date: date, end_date: date
    ) -> List[DailyMetricsResponse]:
        """Get daily metrics"""

        query = (
            select(DailyMetrics)
            .where(
                and_(
                    DailyMetrics.tenant_id == self.tenant_id,
                    DailyMetrics.date >= start_date,
                    DailyMetrics.date <= end_date,
                )
            )
            .order_by(DailyMetrics.date)
        )

        result = await self.db.execute(query)
        metrics = result.scalars().all()

        return [
            DailyMetricsResponse(
                date=m.date,
                revenue=m.total_revenue or Decimal("0"),
                orders=m.total_orders or 0,
                confirmed_orders=m.confirmed_orders or 0,
                shipped_orders=m.shipped_orders or 0,
                delivered_orders=m.delivered_orders or 0,
                cancelled_orders=m.cancelled_orders or 0,
                rto_orders=m.rto_orders or 0,
                cod_orders=m.cod_orders or 0,
                prepaid_orders=m.prepaid_orders or 0,
                cod_percentage=m.cod_percentage or Decimal("0"),
                rto_rate=m.rto_rate or Decimal("0"),
                rto_cost=m.rto_cost or Decimal("0"),
                new_customers=m.new_customers or 0,
                returning_customers=m.returning_customers or 0,
                repeat_purchase_rate=m.repeat_purchase_rate or Decimal("0"),
                cogs=m.total_cogs or Decimal("0"),
                profit=m.total_profit or Decimal("0"),
                profit_margin=m.profit_margin or Decimal("0"),
                marketing_spend=m.marketing_spend or Decimal("0"),
                marketing_revenue=m.marketing_revenue or Decimal("0"),
                marketing_roas=m.roas or Decimal("0"),
                cac=m.cac or Decimal("0"),
                inventory_value=m.total_inventory_value or Decimal("0"),
                stockouts=m.stockout_count or 0,
            )
            for m in metrics
        ]

    async def get_pincode_metrics(
        self,
        limit: int = 100,
        offset: int = 0,
        risk_level: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[PinCodeMetricsResponse]:
        """Get pin code metrics"""

        conditions = [PinCodeMetrics.tenant_id == self.tenant_id]

        if risk_level:
            conditions.append(PinCodeMetrics.risk_level == risk_level)

        if state:
            conditions.append(PinCodeMetrics.state == state)

        query = (
            select(PinCodeMetrics)
            .where(and_(*conditions))
            .order_by(desc(PinCodeMetrics.total_orders))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        metrics = result.scalars().all()

        return [
            PinCodeMetricsResponse(
                pincode=m.pincode,
                city=m.city,
                state=m.state,
                tier=m.tier,
                total_orders=m.total_orders or 0,
                delivered_orders=m.delivered_orders or 0,
                rto_orders=m.rto_orders or 0,
                rto_rate=m.rto_rate or Decimal("0"),
                delivery_success_rate=(
                    Decimal("100") - (m.rto_rate or Decimal("0"))
                    if m.rto_rate
                    else Decimal("100")
                ),
                risk_score=m.risk_score or 50,
                risk_level=m.risk_level or "Medium",
                cod_orders=m.cod_orders or 0,
                cod_percentage=(
                    (m.cod_orders / m.total_orders * 100) if m.total_orders > 0 else Decimal("0")
                ),
                avg_order_value=m.avg_order_value or Decimal("0"),
                avg_delivery_days=m.avg_delivery_days or Decimal("0"),
                last_updated=m.updated_at,
            )
            for m in metrics
        ]

    async def get_cod_rto_analytics(
        self, start_date: date, end_date: date
    ) -> CODRTOAnalytics:
        """Get COD/RTO analytics"""

        # Overall RTO metrics
        overall_query = select(
            func.sum(DailyMetrics.total_orders).label("total_orders"),
            func.sum(DailyMetrics.rto_orders).label("rto_orders"),
            func.sum(DailyMetrics.cod_orders).label("cod_orders"),
            func.sum(DailyMetrics.prepaid_orders).label("prepaid_orders"),
            func.sum(DailyMetrics.rto_cost).label("total_rto_cost"),
        ).where(
            and_(
                DailyMetrics.tenant_id == self.tenant_id,
                DailyMetrics.date >= start_date,
                DailyMetrics.date <= end_date,
            )
        )

        result = await self.db.execute(overall_query)
        overall = result.first()

        total_orders = overall.total_orders or 0
        rto_orders = overall.rto_orders or 0
        cod_orders = overall.cod_orders or 0
        prepaid_orders = overall.prepaid_orders or 0

        overall_rto_rate = (
            Decimal(rto_orders) / Decimal(total_orders) * 100
            if total_orders > 0
            else Decimal("0")
        )

        # COD RTO calculation (simplified - you may want to track this separately)
        cod_rto_rate = overall_rto_rate  # Placeholder
        prepaid_rto_rate = Decimal("0")  # Placeholder

        # Channel breakdown
        channel_query = (
            select(
                Channel.name,
                func.count(Order.id).label("total_orders"),
                func.sum(
                    case((Order.status == OrderStatus.RTO, 1), else_=0)
                ).label("rto_orders"),
            )
            .join(Order, Order.channel_id == Channel.id)
            .where(
                and_(
                    Channel.tenant_id == self.tenant_id,
                    Order.created_at >= datetime.combine(
                        start_date, datetime.min.time()
                    ),
                    Order.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .group_by(Channel.name)
        )

        channel_result = await self.db.execute(channel_query)
        channel_breakdown = [
            {
                "channel": row.name,
                "total_orders": row.total_orders,
                "rto_orders": row.rto_orders or 0,
                "rto_rate": (
                    (row.rto_orders / row.total_orders * 100)
                    if row.total_orders > 0
                    else 0
                ),
            }
            for row in channel_result.all()
        ]

        # Pin code risk distribution
        pincode_dist_query = select(
            func.count(PinCodeMetrics.id).label("count"),
            PinCodeMetrics.risk_level,
        ).where(PinCodeMetrics.tenant_id == self.tenant_id).group_by(
            PinCodeMetrics.risk_level
        )

        pincode_result = await self.db.execute(pincode_dist_query)
        pincode_dist = {row.risk_level: row.count for row in pincode_result.all()}

        return CODRTOAnalytics(
            overall_rto_rate=overall_rto_rate,
            cod_rto_rate=cod_rto_rate,
            prepaid_rto_rate=prepaid_rto_rate,
            total_rto_cost=overall.total_rto_cost or Decimal("0"),
            channel_breakdown=channel_breakdown,
            courier_breakdown=[],  # Implement if courier data available
            category_breakdown=[],  # Implement if category data available
            high_risk_pincodes=pincode_dist.get("High", 0),
            medium_risk_pincodes=pincode_dist.get("Medium", 0),
            low_risk_pincodes=pincode_dist.get("Low", 0),
            total_ndr=0,  # Implement with NDR model
            ndr_resolved=0,
            ndr_pending=0,
            ndr_resolution_rate=Decimal("0"),
        )

    async def get_inventory_analytics(self) -> InventoryAnalytics:
        """Get inventory analytics"""

        # Total inventory value
        inv_query = select(
            func.sum(InventorySnapshot.total_value).label("total_value"),
            func.count(func.distinct(InventorySnapshot.product_variant_id)).label(
                "total_skus"
            ),
        ).where(InventorySnapshot.tenant_id == self.tenant_id)

        inv_result = await self.db.execute(inv_query)
        inv_data = inv_result.first()

        # Stock alerts
        alert_query = (
            select(
                StockAlert.severity,
                func.count(StockAlert.id).label("count"),
            )
            .where(
                and_(
                    StockAlert.tenant_id == self.tenant_id,
                    StockAlert.is_resolved == False,
                )
            )
            .group_by(StockAlert.severity)
        )

        alert_result = await self.db.execute(alert_query)
        alerts = {row.severity: row.count for row in alert_result.all()}

        return InventoryAnalytics(
            total_inventory_value=inv_data.total_value or Decimal("0"),
            total_skus=inv_data.total_skus or 0,
            active_skus=inv_data.total_skus or 0,
            avg_doi=Decimal("30"),  # Placeholder - implement calculation
            inventory_turnover_ratio=Decimal("4.0"),  # Placeholder
            annual_holding_cost_percentage=Decimal("25"),
            estimated_holding_cost=(
                (inv_data.total_value or Decimal("0")) * Decimal("0.25")
            ),
            critical_stockouts=alerts.get("Critical", 0),
            high_stockouts=alerts.get("High", 0),
            medium_stockouts=alerts.get("Medium", 0),
            dead_stock_items=0,  # Implement
            very_slow_moving=0,
            slow_moving=0,
            dead_stock_value=Decimal("0"),
        )
