"""
Razorpay Integration Service for Subscriptions and Payments
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import razorpay
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, Invoice
from app.models.tenant import Tenant
from app.core.config import settings


class RazorpayService:
    """Razorpay Integration Service"""

    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    async def create_customer(
        self,
        db: AsyncSession,
        tenant: Tenant,
        user_email: str,
    ) -> str:
        """
        Create Razorpay customer
        Returns customer_id
        """
        try:
            customer_data = {
                "name": tenant.name,
                "email": user_email,
                "contact": tenant.phone or "",
                "notes": {
                    "tenant_id": str(tenant.id),
                }
            }

            customer = self.client.customer.create(data=customer_data)
            return customer['id']

        except Exception as e:
            raise ValueError(f"Failed to create Razorpay customer: {e}")

    async def create_subscription(
        self,
        db: AsyncSession,
        tenant_id: int,
        plan_id: int,
        customer_id: str,
    ) -> Subscription:
        """
        Create Razorpay subscription
        """
        # Get plan
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()

        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        # Create or get Razorpay plan
        if not plan.razorpay_plan_id:
            razorpay_plan = await self._create_razorpay_plan(plan)
            plan.razorpay_plan_id = razorpay_plan['id']
            await db.commit()

        # Create subscription
        try:
            subscription_data = {
                "plan_id": plan.razorpay_plan_id,
                "customer_notify": 1,
                "total_count": 12,  # 12 months
                "notes": {
                    "tenant_id": str(tenant_id),
                }
            }

            razorpay_subscription = self.client.subscription.create(data=subscription_data)

            # Create subscription record
            subscription = Subscription(
                tenant_id=tenant_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                start_date=datetime.utcnow(),
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
                next_billing_date=datetime.utcnow() + timedelta(days=30),
                razorpay_subscription_id=razorpay_subscription['id'],
                razorpay_customer_id=customer_id,
            )

            db.add(subscription)
            await db.commit()
            await db.refresh(subscription)

            return subscription

        except Exception as e:
            raise ValueError(f"Failed to create subscription: {e}")

    async def cancel_subscription(
        self,
        db: AsyncSession,
        subscription_id: int,
    ) -> bool:
        """
        Cancel Razorpay subscription
        """
        # Get subscription
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription or not subscription.razorpay_subscription_id:
            raise ValueError("Subscription not found")

        try:
            # Cancel on Razorpay
            self.client.subscription.cancel(subscription.razorpay_subscription_id)

            # Update local record
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
            await db.commit()

            return True

        except Exception as e:
            raise ValueError(f"Failed to cancel subscription: {e}")

    async def handle_webhook(
        self,
        db: AsyncSession,
        payload: Dict,
        signature: str,
    ) -> bool:
        """
        Handle Razorpay webhook events
        """
        # Verify signature
        try:
            self.client.utility.verify_webhook_signature(
                str(payload),
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
        except:
            raise ValueError("Invalid webhook signature")

        event_type = payload.get('event')
        subscription_data = payload.get('payload', {}).get('subscription', {}).get('entity', {})

        if event_type == 'subscription.activated':
            await self._handle_subscription_activated(db, subscription_data)
        elif event_type == 'subscription.charged':
            await self._handle_subscription_charged(db, subscription_data, payload.get('payload', {}).get('payment', {}).get('entity', {}))
        elif event_type == 'subscription.cancelled':
            await self._handle_subscription_cancelled(db, subscription_data)
        elif event_type == 'subscription.paused':
            await self._handle_subscription_paused(db, subscription_data)

        return True

    async def _create_razorpay_plan(self, plan: SubscriptionPlan) -> Dict:
        """Create plan on Razorpay"""
        plan_data = {
            "period": "monthly",
            "interval": 1,
            "item": {
                "name": plan.display_name,
                "amount": int(plan.price * 100),  # Convert to paise
                "currency": "INR",
                "description": plan.description,
            },
            "notes": {
                "plan_id": str(plan.id),
            }
        }

        return self.client.plan.create(data=plan_data)

    async def _handle_subscription_activated(self, db: AsyncSession, data: Dict):
        """Handle subscription activated event"""
        razorpay_subscription_id = data.get('id')

        result = await db.execute(
            select(Subscription).where(
                Subscription.razorpay_subscription_id == razorpay_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.ACTIVE
            await db.commit()

    async def _handle_subscription_charged(
        self,
        db: AsyncSession,
        subscription_data: Dict,
        payment_data: Dict
    ):
        """Handle subscription charged event"""
        razorpay_subscription_id = subscription_data.get('id')

        result = await db.execute(
            select(Subscription).where(
                Subscription.razorpay_subscription_id == razorpay_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # Update billing dates
            subscription.last_billing_date = datetime.utcnow()
            subscription.next_billing_date = datetime.utcnow() + timedelta(days=30)
            subscription.current_period_start = datetime.utcnow()
            subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
            subscription.current_period_orders = 0  # Reset usage

            # Create invoice
            invoice = Invoice(
                subscription_id=subscription.id,
                tenant_id=subscription.tenant_id,
                invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                invoice_date=datetime.utcnow(),
                due_date=datetime.utcnow() + timedelta(days=7),
                subtotal=subscription.plan.price,
                tax_amount=subscription.plan.price * 0.18,  # 18% GST
                total_amount=subscription.plan.price * 1.18,
                status="paid",
                paid_at=datetime.utcnow(),
                razorpay_payment_id=payment_data.get('id'),
            )
            db.add(invoice)

            await db.commit()

    async def _handle_subscription_cancelled(self, db: AsyncSession, data: Dict):
        """Handle subscription cancelled event"""
        razorpay_subscription_id = data.get('id')

        result = await db.execute(
            select(Subscription).where(
                Subscription.razorpay_subscription_id == razorpay_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
            await db.commit()

    async def _handle_subscription_paused(self, db: AsyncSession, data: Dict):
        """Handle subscription paused event"""
        razorpay_subscription_id = data.get('id')

        result = await db.execute(
            select(Subscription).where(
                Subscription.razorpay_subscription_id == razorpay_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            await db.commit()

    async def check_usage_limit(
        self,
        db: AsyncSession,
        tenant_id: int,
    ) -> Dict:
        """
        Check if tenant has exceeded usage limits
        """
        # Get subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return {"allowed": False, "reason": "No active subscription"}

        # Check order limit
        usage_percentage = (subscription.current_period_orders / subscription.plan.max_orders_per_month) * 100

        if subscription.current_period_orders >= subscription.plan.max_orders_per_month:
            return {
                "allowed": False,
                "reason": "Order limit exceeded",
                "usage_percentage": usage_percentage,
                "current_usage": subscription.current_period_orders,
                "limit": subscription.plan.max_orders_per_month,
            }

        return {
            "allowed": True,
            "usage_percentage": usage_percentage,
            "current_usage": subscription.current_period_orders,
            "limit": subscription.plan.max_orders_per_month,
            "warning": usage_percentage >= 80,
        }


# Global Razorpay service instance
razorpay_service = RazorpayService()
