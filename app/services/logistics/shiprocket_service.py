"""
Shiprocket Integration Service for Logistics Management
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.order import Order
from app.models.shipment import Shipment, ShipmentStatus, NDRReport
from app.core.config import settings


class ShiprocketService:
    """Shiprocket Integration Service"""

    BASE_URL = "https://apiv2.shiprocket.in/v1/external"

    def __init__(self):
        self.token = None
        self.token_expires_at = None

    async def authenticate(self) -> str:
        """
        Authenticate with Shiprocket and get access token
        """
        if self.token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/login",
                json={
                    "email": settings.SHIPROCKET_EMAIL,
                    "password": settings.SHIPROCKET_PASSWORD,
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data['token']
                # Token typically expires in 10 days
                self.token_expires_at = datetime.now() + timedelta(days=9)
                return self.token
            else:
                raise Exception(f"Shiprocket authentication failed: {response.text}")

    async def create_order(
        self,
        db: AsyncSession,
        order: Order,
    ) -> Dict:
        """
        Create order on Shiprocket
        """
        token = await self.authenticate()

        # Prepare order data
        order_items = []
        for item in order.items:
            order_items.append({
                "name": item.product_name,
                "sku": item.sku,
                "units": item.quantity,
                "selling_price": str(item.unit_price),
                "discount": "0",
                "tax": str(item.tax_amount),
                "hsn": item.hsn_code or "",
            })

        order_data = {
            "order_id": order.order_number,
            "order_date": order.order_date.strftime("%Y-%m-%d %H:%M"),
            "pickup_location": "Primary",  # Default warehouse
            "channel_id": "",  # Custom
            "comment": order.notes or "",
            "billing_customer_name": order.customer_name,
            "billing_last_name": "",
            "billing_address": order.billing_address_line1,
            "billing_address_2": order.billing_address_line2 or "",
            "billing_city": order.billing_city,
            "billing_pincode": order.billing_pincode,
            "billing_state": order.billing_state,
            "billing_country": "India",
            "billing_email": order.customer_email or "",
            "billing_phone": order.customer_phone,
            "shipping_is_billing": order.shipping_pincode == order.billing_pincode,
            "shipping_customer_name": order.customer_name,
            "shipping_last_name": "",
            "shipping_address": order.shipping_address_line1,
            "shipping_address_2": order.shipping_address_line2 or "",
            "shipping_city": order.shipping_city,
            "shipping_pincode": order.shipping_pincode,
            "shipping_country": "India",
            "shipping_state": order.shipping_state,
            "shipping_email": order.customer_email or "",
            "shipping_phone": order.customer_phone,
            "order_items": order_items,
            "payment_method": "COD" if order.payment_method.value == "cod" else "Prepaid",
            "shipping_charges": str(order.shipping_charges),
            "giftwrap_charges": "0",
            "transaction_charges": "0",
            "total_discount": str(order.discount_amount),
            "sub_total": str(order.subtotal),
            "length": "10",  # Default dimensions in cm
            "breadth": "10",
            "height": "10",
            "weight": "0.5",  # Default weight in kg
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/orders/create/adhoc",
                json=order_data,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                raise Exception(f"Failed to create Shiprocket order: {response.text}")

    async def generate_awb(
        self,
        db: AsyncSession,
        shipment_id: int,
        courier_id: Optional[int] = None,
    ) -> str:
        """
        Generate AWB (Air Waybill) for shipment
        """
        token = await self.authenticate()

        # Get shipment
        result = await db.execute(
            select(Shipment).where(Shipment.id == shipment_id)
        )
        shipment = result.scalar_one_or_none()

        if not shipment or not shipment.shiprocket_shipment_id:
            raise ValueError("Shipment not found or not created on Shiprocket")

        # Get recommended courier if not provided
        if not courier_id:
            courier_id = await self._get_recommended_courier(
                shipment.shiprocket_shipment_id,
                token
            )

        awb_data = {
            "shipment_id": int(shipment.shiprocket_shipment_id),
            "courier_id": courier_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/courier/assign/awb",
                json=awb_data,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                data = response.json()
                awb = data['response']['data']['awb_code']

                # Update shipment
                shipment.awb_number = awb
                shipment.courier_id = str(courier_id)
                shipment.status = ShipmentStatus.PICKUP_SCHEDULED
                await db.commit()

                return awb
            else:
                raise Exception(f"Failed to generate AWB: {response.text}")

    async def request_pickup(
        self,
        db: AsyncSession,
        shipment_ids: List[int],
    ) -> bool:
        """
        Request pickup for shipments
        """
        token = await self.authenticate()

        # Get Shiprocket shipment IDs
        result = await db.execute(
            select(Shipment).where(Shipment.id.in_(shipment_ids))
        )
        shipments = result.scalars().all()

        shiprocket_ids = [int(s.shiprocket_shipment_id) for s in shipments if s.shiprocket_shipment_id]

        if not shiprocket_ids:
            raise ValueError("No valid shipments found")

        pickup_data = {
            "shipment_id": shiprocket_ids,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/courier/generate/pickup",
                json=pickup_data,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                # Update shipments
                for shipment in shipments:
                    shipment.status = ShipmentStatus.PICKUP_SCHEDULED
                    shipment.pickup_scheduled_at = datetime.utcnow()
                await db.commit()

                return True
            else:
                raise Exception(f"Failed to request pickup: {response.text}")

    async def track_shipment(
        self,
        db: AsyncSession,
        shipment_id: int,
    ) -> Dict:
        """
        Track shipment status
        """
        token = await self.authenticate()

        # Get shipment
        result = await db.execute(
            select(Shipment).where(Shipment.id == shipment_id)
        )
        shipment = result.scalar_one_or_none()

        if not shipment or not shipment.shiprocket_shipment_id:
            raise ValueError("Shipment not found")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/courier/track/shipment/{shipment.shiprocket_shipment_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                data = response.json()
                tracking_data = data.get('tracking_data', {})

                # Update shipment status
                await self._update_shipment_status(db, shipment, tracking_data)

                return tracking_data
            else:
                raise Exception(f"Failed to track shipment: {response.text}")

    async def get_ndr_details(
        self,
        db: AsyncSession,
        awb: str,
    ) -> Optional[Dict]:
        """
        Get NDR (Non-Delivery Report) details for a shipment
        """
        token = await self.authenticate()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/courier/track/awb/{awb}",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                return None

    async def update_ndr_action(
        self,
        db: AsyncSession,
        shipment_id: int,
        action: str,
        reattempt_date: Optional[datetime] = None,
    ) -> bool:
        """
        Update NDR action (reattempt/RTO)
        action: 'reattempt' or 'rto'
        """
        token = await self.authenticate()

        # Get shipment
        result = await db.execute(
            select(Shipment).where(Shipment.id == shipment_id)
        )
        shipment = result.scalar_one_or_none()

        if not shipment or not shipment.awb_number:
            raise ValueError("Shipment or AWB not found")

        ndr_data = {
            "awb": shipment.awb_number,
            "action": action,
        }

        if action == "reattempt" and reattempt_date:
            ndr_data["reattempt_date"] = reattempt_date.strftime("%Y-%m-%d")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/courier/update/ndr",
                json=ndr_data,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                # Update NDR report
                result = await db.execute(
                    select(NDRReport)
                    .where(NDRReport.shipment_id == shipment_id)
                    .order_by(NDRReport.created_at.desc())
                    .limit(1)
                )
                ndr = result.scalar_one_or_none()

                if ndr:
                    ndr.action_taken = action
                    ndr.action_date = datetime.utcnow()
                    if reattempt_date:
                        ndr.reattempt_date = reattempt_date
                    await db.commit()

                return True
            else:
                raise Exception(f"Failed to update NDR: {response.text}")

    async def _get_recommended_courier(
        self,
        shipment_id: str,
        token: str,
    ) -> int:
        """Get recommended courier for shipment"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/courier/serviceability/?shipment_id={shipment_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                data = response.json()
                couriers = data.get('data', {}).get('available_courier_companies', [])

                if couriers:
                    # Return the first recommended courier
                    return couriers[0]['id']
                else:
                    raise Exception("No couriers available for this shipment")
            else:
                raise Exception("Failed to get courier recommendations")

    async def _update_shipment_status(
        self,
        db: AsyncSession,
        shipment: Shipment,
        tracking_data: Dict,
    ):
        """Update shipment status from tracking data"""
        status_map = {
            "Delivered": ShipmentStatus.DELIVERED,
            "Out For Delivery": ShipmentStatus.OUT_FOR_DELIVERY,
            "In Transit": ShipmentStatus.IN_TRANSIT,
            "Picked Up": ShipmentStatus.PICKED_UP,
            "RTO": ShipmentStatus.RTO,
            "Failed": ShipmentStatus.FAILED,
        }

        current_status = tracking_data.get('shipment_status')
        if current_status and current_status in status_map:
            shipment.status = status_map[current_status]
            shipment.current_location = tracking_data.get('current_location', '')

            if current_status == "Delivered":
                shipment.delivered_at = datetime.utcnow()
            elif current_status == "Picked Up":
                shipment.picked_up_at = datetime.utcnow()
            elif current_status == "RTO":
                shipment.rto_initiated_at = datetime.utcnow()

            # Store tracking events
            shipment.tracking_events = tracking_data.get('shipment_track', [])

            await db.commit()


# Global Shiprocket service instance
shiprocket_service = ShiprocketService()
