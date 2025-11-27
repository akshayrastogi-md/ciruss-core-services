"""
Report generation service
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import io
from decimal import Decimal

from app.models.report import Report, ReportSchedule
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductVariant
from app.models.channel import Channel
from app.models.analytics import DailyMetrics, PinCodeMetrics
from app.models.marketing import AdSpend, MarketingCampaign
from app.schemas.report import ReportType, ReportFormat, ReportStatus


class ReportService:
    """Report generation service"""

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def create_report(
        self,
        report_type: str,
        start_date: date,
        end_date: date,
        format: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Report:
        """Create a report"""

        report = Report(
            tenant_id=self.tenant_id,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            format=format,
            filters=filters or {},
            status=ReportStatus.PENDING,
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        return report

    async def get_report(self, report_id: int) -> Optional[Report]:
        """Get a report by ID"""

        query = select(Report).where(
            and_(Report.tenant_id == self.tenant_id, Report.id == report_id)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Report]:
        """List reports"""

        conditions = [Report.tenant_id == self.tenant_id]

        if report_type:
            conditions.append(Report.report_type == report_type)

        if status:
            conditions.append(Report.status == status)

        query = (
            select(Report)
            .where(and_(*conditions))
            .order_by(Report.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_schedule(
        self,
        report_type: str,
        frequency: str,
        format: str,
        recipients: List[str],
        filters: Optional[Dict[str, Any]] = None,
    ) -> ReportSchedule:
        """Create a report schedule"""

        # Calculate next run time
        now = datetime.utcnow()
        if frequency == "daily":
            next_run = now.replace(hour=9, minute=0, second=0) + timedelta(days=1)
        elif frequency == "weekly":
            next_run = now.replace(hour=9, minute=0, second=0) + timedelta(days=7)
        elif frequency == "monthly":
            next_run = now.replace(hour=9, minute=0, second=0) + timedelta(days=30)
        else:
            next_run = now + timedelta(days=1)

        schedule = ReportSchedule(
            tenant_id=self.tenant_id,
            report_type=report_type,
            frequency=frequency,
            format=format,
            recipients=recipients,
            filters=filters or {},
            is_active=True,
            next_run_at=next_run,
        )

        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)

        return schedule

    async def get_schedule(self, schedule_id: int) -> Optional[ReportSchedule]:
        """Get a schedule by ID"""

        query = select(ReportSchedule).where(
            and_(
                ReportSchedule.tenant_id == self.tenant_id,
                ReportSchedule.id == schedule_id,
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_schedules(
        self, is_active: Optional[bool] = None, limit: int = 50, offset: int = 0
    ) -> List[ReportSchedule]:
        """List report schedules"""

        conditions = [ReportSchedule.tenant_id == self.tenant_id]

        if is_active is not None:
            conditions.append(ReportSchedule.is_active == is_active)

        query = (
            select(ReportSchedule)
            .where(and_(*conditions))
            .order_by(ReportSchedule.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_schedule(
        self,
        schedule_id: int,
        frequency: Optional[str] = None,
        format: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[ReportSchedule]:
        """Update a report schedule"""

        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return None

        if frequency is not None:
            schedule.frequency = frequency

        if format is not None:
            schedule.format = format

        if recipients is not None:
            schedule.recipients = recipients

        if filters is not None:
            schedule.filters = filters

        if is_active is not None:
            schedule.is_active = is_active

        await self.db.commit()
        await self.db.refresh(schedule)

        return schedule

    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a report schedule"""

        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return False

        await self.db.delete(schedule)
        await self.db.commit()

        return True

    async def generate_sales_report(
        self, start_date: date, end_date: date, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate sales report data"""

        conditions = [
            Order.tenant_id == self.tenant_id,
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
        ]

        # Apply filters
        if filters.get("channel_id"):
            conditions.append(Order.channel_id == filters["channel_id"])

        if filters.get("status"):
            conditions.append(Order.status == filters["status"])

        query = (
            select(Order)
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
        )

        result = await self.db.execute(query)
        orders = result.scalars().all()

        # Aggregate data
        total_orders = len(orders)
        total_revenue = sum(order.total_amount or Decimal("0") for order in orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else Decimal("0")

        return {
            "summary": {
                "total_orders": total_orders,
                "total_revenue": float(total_revenue),
                "avg_order_value": float(avg_order_value),
            },
            "orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "created_at": order.created_at.isoformat(),
                    "customer_name": order.customer_name,
                    "total_amount": float(order.total_amount or Decimal("0")),
                    "payment_method": order.payment_method,
                    "status": order.status.value if hasattr(order.status, "value") else order.status,
                }
                for order in orders
            ],
        }

    async def generate_product_performance_report(
        self, start_date: date, end_date: date, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate product performance report data"""

        query = (
            select(
                Product.id,
                Product.name,
                ProductVariant.sku,
                func.sum(OrderItem.quantity).label("quantity_sold"),
                func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
                func.count(func.distinct(Order.id)).label("order_count"),
            )
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .join(OrderItem, OrderItem.product_variant_id == ProductVariant.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                and_(
                    Product.tenant_id == self.tenant_id,
                    Order.created_at >= datetime.combine(start_date, datetime.min.time()),
                    Order.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .group_by(Product.id, Product.name, ProductVariant.sku)
            .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
        )

        result = await self.db.execute(query)
        products = result.all()

        return {
            "products": [
                {
                    "product_id": p.id,
                    "product_name": p.name,
                    "sku": p.sku,
                    "quantity_sold": p.quantity_sold or 0,
                    "revenue": float(p.revenue or Decimal("0")),
                    "order_count": p.order_count or 0,
                }
                for p in products
            ]
        }

    async def generate_rto_analysis_report(
        self, start_date: date, end_date: date, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate RTO analysis report data"""

        query = select(
            func.sum(DailyMetrics.total_orders).label("total_orders"),
            func.sum(DailyMetrics.rto_orders).label("rto_orders"),
            func.sum(DailyMetrics.rto_cost).label("total_rto_cost"),
            func.avg(DailyMetrics.rto_rate).label("avg_rto_rate"),
        ).where(
            and_(
                DailyMetrics.tenant_id == self.tenant_id,
                DailyMetrics.date >= start_date,
                DailyMetrics.date <= end_date,
            )
        )

        result = await self.db.execute(query)
        data = result.first()

        # Pin code breakdown
        pincode_query = (
            select(
                PinCodeMetrics.pincode,
                PinCodeMetrics.state,
                PinCodeMetrics.total_orders,
                PinCodeMetrics.rto_orders,
                PinCodeMetrics.rto_rate,
                PinCodeMetrics.risk_level,
            )
            .where(PinCodeMetrics.tenant_id == self.tenant_id)
            .order_by(PinCodeMetrics.rto_rate.desc())
            .limit(50)
        )

        pincode_result = await self.db.execute(pincode_query)
        pincodes = pincode_result.all()

        return {
            "summary": {
                "total_orders": data.total_orders or 0,
                "rto_orders": data.rto_orders or 0,
                "total_rto_cost": float(data.total_rto_cost or Decimal("0")),
                "avg_rto_rate": float(data.avg_rto_rate or Decimal("0")),
            },
            "pincode_breakdown": [
                {
                    "pincode": p.pincode,
                    "state": p.state,
                    "total_orders": p.total_orders,
                    "rto_orders": p.rto_orders,
                    "rto_rate": float(p.rto_rate or Decimal("0")),
                    "risk_level": p.risk_level,
                }
                for p in pincodes
            ],
        }

    async def generate_marketing_performance_report(
        self, start_date: date, end_date: date, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate marketing performance report data"""

        query = (
            select(
                MarketingCampaign.platform,
                MarketingCampaign.campaign_name,
                func.sum(AdSpend.spend).label("total_spend"),
                func.sum(AdSpend.impressions).label("total_impressions"),
                func.sum(AdSpend.clicks).label("total_clicks"),
                func.sum(AdSpend.conversions).label("total_conversions"),
                func.sum(AdSpend.revenue).label("total_revenue"),
            )
            .join(AdSpend, AdSpend.campaign_id == MarketingCampaign.id)
            .where(
                and_(
                    MarketingCampaign.tenant_id == self.tenant_id,
                    AdSpend.date >= start_date,
                    AdSpend.date <= end_date,
                )
            )
            .group_by(MarketingCampaign.platform, MarketingCampaign.campaign_name)
        )

        result = await self.db.execute(query)
        campaigns = result.all()

        return {
            "campaigns": [
                {
                    "platform": c.platform,
                    "campaign_name": c.campaign_name,
                    "total_spend": float(c.total_spend or Decimal("0")),
                    "total_impressions": c.total_impressions or 0,
                    "total_clicks": c.total_clicks or 0,
                    "total_conversions": c.total_conversions or 0,
                    "total_revenue": float(c.total_revenue or Decimal("0")),
                    "roas": (
                        float(c.total_revenue / c.total_spend)
                        if c.total_spend and c.total_spend > 0
                        else 0.0
                    ),
                }
                for c in campaigns
            ]
        }
