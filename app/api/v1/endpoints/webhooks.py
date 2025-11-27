"""
Webhook endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import hmac
import hashlib
import json

from app.core.deps import get_db
from app.models.subscription import Subscription
from app.models.shipment import Shipment, ShipmentStatus
from app.models.order import Order, OrderStatus
from app.services.razorpay_service import RazorpayService
from sqlalchemy import select, and_

router = APIRouter()


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Razorpay webhook handler

    Handles subscription events from Razorpay (activated, charged, cancelled, etc.).
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        # Verify signature (in production, use actual webhook secret)
        # webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        # expected_signature = hmac.new(
        #     webhook_secret.encode(),
        #     body,
        #     hashlib.sha256
        # ).hexdigest()
        #
        # if not hmac.compare_digest(expected_signature, x_razorpay_signature or ""):
        #     raise HTTPException(status_code=400, detail="Invalid signature")

        event = payload.get("event")
        entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})

        razorpay_subscription_id = entity.get("id")

        if not razorpay_subscription_id:
            return {"status": "ignored", "reason": "No subscription ID"}

        # Find subscription
        query = select(Subscription).where(
            Subscription.razorpay_subscription_id == razorpay_subscription_id
        )
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()

        if not subscription:
            return {"status": "ignored", "reason": "Subscription not found"}

        # Handle different events
        if event == "subscription.activated":
            subscription.status = "active"
            subscription.current_period_start = entity.get("current_start")
            subscription.current_period_end = entity.get("current_end")

        elif event == "subscription.charged":
            # Create invoice record
            from app.models.subscription import Invoice
            from datetime import datetime

            invoice = Invoice(
                subscription_id=subscription.id,
                invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{subscription.id}",
                razorpay_invoice_id=entity.get("id"),
                amount=entity.get("amount", 0) / 100,  # Convert from paisa
                tax=0,
                total=entity.get("amount", 0) / 100,
                status="paid",
                invoice_date=datetime.utcnow(),
                due_date=datetime.utcnow(),
                paid_at=datetime.utcnow(),
            )
            db.add(invoice)

        elif event == "subscription.cancelled":
            subscription.status = "cancelled"

        elif event == "subscription.paused":
            subscription.status = "paused"

        elif event == "subscription.resumed":
            subscription.status = "active"

        elif event == "subscription.pending":
            subscription.status = "pending"

        await db.commit()

        return {"status": "success", "event": event}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook processing failed: {str(e)}")


@router.post("/shiprocket")
async def shiprocket_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Shiprocket webhook handler

    Handles shipment tracking updates from Shiprocket.
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        # Get event details
        event_type = payload.get("event")
        shipment_data = payload.get("data", {})

        awb = shipment_data.get("awb")
        order_id = shipment_data.get("order_id")

        if not awb:
            return {"status": "ignored", "reason": "No AWB provided"}

        # Find shipment
        query = select(Shipment).where(Shipment.awb_number == awb)
        result = await db.execute(query)
        shipment = result.scalar_one_or_none()

        if not shipment:
            return {"status": "ignored", "reason": "Shipment not found"}

        # Update shipment status based on event
        status_mapping = {
            "PICKUP_SCHEDULED": ShipmentStatus.PICKUP_SCHEDULED,
            "PICKED_UP": ShipmentStatus.PICKED_UP,
            "IN_TRANSIT": ShipmentStatus.IN_TRANSIT,
            "OUT_FOR_DELIVERY": ShipmentStatus.OUT_FOR_DELIVERY,
            "DELIVERED": ShipmentStatus.DELIVERED,
            "RTO_INITIATED": ShipmentStatus.RTO,
            "RTO_DELIVERED": ShipmentStatus.RTO,
            "CANCELLED": ShipmentStatus.CANCELLED,
        }

        new_status = status_mapping.get(event_type)
        if new_status:
            shipment.status = new_status

            # Update order status if delivered or RTO
            if new_status == ShipmentStatus.DELIVERED:
                order_query = select(Order).where(Order.id == shipment.order_id)
                order_result = await db.execute(order_query)
                order = order_result.scalar_one_or_none()
                if order:
                    order.status = OrderStatus.DELIVERED

            elif new_status == ShipmentStatus.RTO:
                order_query = select(Order).where(Order.id == shipment.order_id)
                order_result = await db.execute(order_query)
                order = order_result.scalar_one_or_none()
                if order:
                    order.status = OrderStatus.RTO

        await db.commit()

        return {"status": "success", "event": event_type}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook processing failed: {str(e)}")


@router.post("/shopify")
async def shopify_webhook(
    request: Request,
    x_shopify_topic: Optional[str] = Header(None),
    x_shopify_hmac_sha256: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Shopify webhook handler

    Handles order and product update events from Shopify.
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        # Verify HMAC (in production)
        # shop_secret = get_shopify_secret_for_shop(shop_domain)
        # computed_hmac = base64.b64encode(
        #     hmac.new(shop_secret.encode(), body, hashlib.sha256).digest()
        # ).decode()
        #
        # if not hmac.compare_digest(computed_hmac, x_shopify_hmac_sha256 or ""):
        #     raise HTTPException(status_code=401, detail="Invalid HMAC")

        topic = x_shopify_topic or ""

        if topic == "orders/create":
            # Handle new order
            order_data = payload
            # Process order creation
            pass

        elif topic == "orders/updated":
            # Handle order update
            order_data = payload
            # Process order update
            pass

        elif topic == "products/create":
            # Handle new product
            product_data = payload
            # Process product creation
            pass

        elif topic == "products/update":
            # Handle product update
            product_data = payload
            # Process product update
            pass

        return {"status": "success", "topic": topic}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook processing failed: {str(e)}")


@router.post("/woocommerce")
async def woocommerce_webhook(
    request: Request,
    x_wc_webhook_topic: Optional[str] = Header(None),
    x_wc_webhook_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    WooCommerce webhook handler

    Handles order and product update events from WooCommerce.
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        # Verify signature (in production)
        # webhook_secret = get_woocommerce_secret(store_url)
        # computed_signature = base64.b64encode(
        #     hmac.new(webhook_secret.encode(), body, hashlib.sha256).digest()
        # ).decode()
        #
        # if not hmac.compare_digest(computed_signature, x_wc_webhook_signature or ""):
        #     raise HTTPException(status_code=401, detail="Invalid signature")

        topic = x_wc_webhook_topic or ""

        if topic == "order.created":
            # Handle new order
            order_data = payload
            # Process order creation
            pass

        elif topic == "order.updated":
            # Handle order update
            order_data = payload
            # Process order update
            pass

        elif topic == "product.created":
            # Handle new product
            product_data = payload
            # Process product creation
            pass

        elif topic == "product.updated":
            # Handle product update
            product_data = payload
            # Process product update
            pass

        return {"status": "success", "topic": topic}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook processing failed: {str(e)}")
