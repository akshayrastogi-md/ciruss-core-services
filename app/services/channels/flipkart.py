"""
Flipkart Seller API channel integration service - Complete Implementation
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.services.channels.base import BaseChannelService
from app.models.channel import Channel
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.product import Product
from app.core.security import decrypt_data
import json
import base64


class FlipkartService(BaseChannelService):
    """Flipkart Seller API integration"""

    def __init__(self):
        self.base_url = "https://api.flipkart.net/sellers"
        self.sandbox_url = "https://sandbox-api.flipkart.net/sellers"
        self.token_endpoint = "/oauth-service/oauth/token"
        self.access_token = None
        self.token_expires_at = None

    async def authenticate(self, credentials: Dict) -> bool:
        """
        Authenticate with Flipkart Seller API using OAuth 2.0

        Required credentials:
        - app_id: Flipkart application ID
        - app_secret: Flipkart application secret
        - seller_id: Flipkart seller ID
        - sandbox: (optional) Use sandbox environment for testing
        """
        try:
            app_id = credentials.get('app_id')
            app_secret = credentials.get('app_secret')
            seller_id = credentials.get('seller_id')
            use_sandbox = credentials.get('sandbox', False)

            if not all([app_id, app_secret, seller_id]):
                return False

            # Determine base URL
            base_url = self.sandbox_url if use_sandbox else self.base_url

            # Create Basic Auth header
            credentials_str = f"{app_id}:{app_secret}"
            encoded_credentials = base64.b64encode(credentials_str.encode()).decode()

            # Get access token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}{self.token_endpoint}",
                    headers={
                        'Authorization': f'Basic {encoded_credentials}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'grant_type': 'client_credentials',
                        'scope': 'Seller_Api',
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data.get('access_token')
                    # Token typically expires in 3600 seconds
                    expires_in = token_data.get('expires_in', 3600)
                    self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    return True

                return False

        except Exception as e:
            print(f"Flipkart authentication error: {e}")
            return False

    async def _get_access_token(self, credentials: Dict) -> Optional[str]:
        """Get valid access token, refresh if needed"""
        if self.access_token and self.token_expires_at:
            # Check if token is still valid (with 5 min buffer)
            if datetime.utcnow() < self.token_expires_at - timedelta(minutes=5):
                return self.access_token

        # Need to refresh token
        if await self.authenticate(credentials):
            return self.access_token

        return None

    async def _make_flipkart_request(
        self,
        credentials: Dict,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Make authenticated request to Flipkart Seller API"""
        access_token = await self._get_access_token(credentials)
        if not access_token:
            raise Exception("Failed to get Flipkart access token")

        use_sandbox = credentials.get('sandbox', False)
        base_url = self.sandbox_url if use_sandbox else self.base_url

        url = f"{base_url}{endpoint}"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=json_data, timeout=30.0)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=json_data, timeout=30.0)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, json=json_data, timeout=30.0)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Flipkart API error: {response.status_code} - {response.text}")
                return None

    async def sync_orders(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync orders from Flipkart Seller API
        Returns number of orders synced
        """
        credentials = self._get_credentials(channel)
        synced_count = 0

        # Get orders from Flipkart (filter by date)
        # Flipkart uses order item IDs, not order IDs
        filter_params = {
            'filter': {
                'states': ['APPROVED', 'PACKING_IN_PROGRESS', 'READY_TO_DISPATCH',
                          'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED'],
                'type': 'postOrder',
            }
        }

        response = await self._make_flipkart_request(
            credentials,
            '/v3/orders/search',
            method='POST',
            json_data=filter_params,
        )

        if not response or 'orderItems' not in response:
            return 0

        order_items_data = response.get('orderItems', [])

        # Group order items by orderId
        orders_map = {}
        for item in order_items_data:
            order_id = item.get('orderId')
            if order_id not in orders_map:
                orders_map[order_id] = []
            orders_map[order_id].append(item)

        # Process each order
        for order_id, items in orders_map.items():
            # Check if order exists
            result = await db.execute(
                select(Order).where(
                    and_(
                        Order.channel_id == channel.id,
                        Order.external_order_id == order_id,
                    )
                )
            )
            existing_order = result.scalar_one_or_none()

            if existing_order:
                await self._update_order(db, existing_order, items[0])
            else:
                await self._create_order(db, channel, order_id, items)
                synced_count += 1

        await db.commit()
        return synced_count

    async def sync_products(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync products from Flipkart Seller API
        Returns number of products synced
        """
        credentials = self._get_credentials(channel)
        synced_count = 0

        # Get listings from Flipkart
        response = await self._make_flipkart_request(
            credentials,
            '/v3/listings',
            params={'status': 'APPROVED'},
        )

        if not response or 'listings' not in response:
            return 0

        listings = response.get('listings', [])

        for listing in listings:
            fsn = listing.get('fsn')  # Flipkart Serial Number
            sku = listing.get('sku')

            # Check if product exists with this SKU
            result = await db.execute(
                select(Product).where(
                    and_(
                        Product.tenant_id == channel.tenant_id,
                        Product.sku == sku,
                    )
                )
            )
            existing_product = result.scalar_one_or_none()

            if existing_product:
                # Update channel mapping
                if not existing_product.channel_mappings:
                    existing_product.channel_mappings = {}
                existing_product.channel_mappings[str(channel.id)] = fsn
                await self._update_product(db, existing_product, listing)
            else:
                await self._create_product(db, channel, listing)
                synced_count += 1

        await db.commit()
        return synced_count

    async def sync_inventory(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync inventory from Flipkart Seller API
        Returns number of items synced
        """
        credentials = self._get_credentials(channel)

        # Get products with Flipkart mappings
        result = await db.execute(
            select(Product).where(
                and_(
                    Product.tenant_id == channel.tenant_id,
                    Product.channel_mappings.has_key(str(channel.id)),
                )
            )
        )
        products = result.scalars().all()

        synced_count = 0

        # Get inventory for each SKU
        for product in products:
            # Get inventory
            response = await self._make_flipkart_request(
                credentials,
                f'/v3/listings/{product.sku}/inventory',
            )

            if response and 'inventory' in response:
                inventory_data = response['inventory']
                quantity = inventory_data.get('quantity', 0)
                product.total_stock = quantity
                synced_count += 1

        await db.commit()
        return synced_count

    async def create_order(self, db: AsyncSession, channel: Channel, order_data: Dict) -> Dict:
        """
        Create order on Flipkart

        Note: Flipkart doesn't allow creating orders programmatically.
        Orders are created by customers on Flipkart marketplace.
        This method is not applicable for Flipkart channel.
        """
        raise NotImplementedError(
            "Flipkart Seller API does not support creating orders programmatically. "
            "Orders are created by customers on Flipkart marketplace."
        )

    async def update_order_status(
        self,
        db: AsyncSession,
        channel: Channel,
        external_order_id: str,
        status: str,
    ) -> bool:
        """
        Update order status on Flipkart

        Uses Shipments API to update dispatch and delivery status
        """
        credentials = self._get_credentials(channel)

        # Map internal status to Flipkart actions
        if status == 'shipped':
            # Mark as ready to dispatch or dispatch
            # This requires shipment details
            # Simplified implementation
            return await self._mark_ready_to_dispatch(credentials, external_order_id)
        elif status == 'cancelled':
            # Cancel order
            return await self._cancel_order(credentials, external_order_id)

        return True

    async def _mark_ready_to_dispatch(self, credentials: Dict, order_item_id: str) -> bool:
        """Mark order item as ready to dispatch"""
        response = await self._make_flipkart_request(
            credentials,
            '/v3/shipments',
            method='POST',
            json_data={
                'orderItems': [{'orderItemId': order_item_id}],
                'locationId': credentials.get('location_id', 'default'),
            },
        )
        return response is not None

    async def _cancel_order(self, credentials: Dict, order_item_id: str) -> bool:
        """Cancel order item"""
        response = await self._make_flipkart_request(
            credentials,
            f'/v3/orders/{order_item_id}/cancel',
            method='POST',
            json_data={
                'reason': 'SELLER_CANCELLED',
            },
        )
        return response is not None

    def _get_credentials(self, channel: Channel) -> Dict:
        """Decrypt and return channel credentials"""
        if not channel.credentials or not channel.credentials.encrypted_credentials:
            raise ValueError("Channel credentials not configured")

        decrypted = decrypt_data(channel.credentials.encrypted_credentials)
        return json.loads(decrypted)

    async def _create_order(
        self,
        db: AsyncSession,
        channel: Channel,
        order_id: str,
        order_items: List[Dict],
    ):
        """Create order from Flipkart data"""
        from decimal import Decimal

        # Get primary order item for order-level details
        primary_item = order_items[0]

        # Map payment method
        payment_method = PaymentMethod.PREPAID
        if primary_item.get('paymentType') == 'COD':
            payment_method = PaymentMethod.COD

        # Parse order date
        order_date_str = primary_item.get('orderDate', '')
        try:
            order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
        except:
            order_date = datetime.utcnow()

        # Get shipping address
        shipping_address = primary_item.get('shippingAddress', {})

        # Calculate totals
        total_amount = Decimal('0')
        for item in order_items:
            pricing = item.get('priceComponents', {})
            total_amount += Decimal(str(pricing.get('totalPrice', 0)))

        # Create order
        order = Order(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            order_number=order_id,
            external_order_id=order_id,
            order_date=order_date,
            status=self._map_flipkart_status(primary_item.get('state', 'APPROVED')),
            customer_name=shipping_address.get('name', 'Flipkart Customer'),
            customer_email='',  # Flipkart doesn't provide customer email
            customer_phone=shipping_address.get('phone', ''),
            shipping_address_line1=shipping_address.get('addressLine1', ''),
            shipping_address_line2=shipping_address.get('addressLine2', ''),
            shipping_city=shipping_address.get('city', ''),
            shipping_state=shipping_address.get('state', ''),
            shipping_pincode=shipping_address.get('pincode', ''),
            billing_address_line1=shipping_address.get('addressLine1', ''),
            billing_address_line2=shipping_address.get('addressLine2', ''),
            billing_city=shipping_address.get('city', ''),
            billing_state=shipping_address.get('state', ''),
            billing_pincode=shipping_address.get('pincode', ''),
            payment_method=payment_method,
            subtotal=total_amount,
            discount_amount=Decimal('0'),
            tax_amount=Decimal('0'),
            shipping_charges=Decimal('0'),
            total_amount=total_amount,
        )

        db.add(order)
        await db.flush()

        # Add order items
        for item in order_items:
            pricing = item.get('priceComponents', {})

            order_item = OrderItem(
                tenant_id=channel.tenant_id,
                order_id=order.id,
                product_name=item.get('title', ''),
                sku=item.get('sku', ''),
                unit_price=Decimal(str(pricing.get('sellingPrice', 0))),
                quantity=item.get('quantity', 1),
                tax_amount=Decimal(str(pricing.get('totalPrice', 0))) - Decimal(str(pricing.get('sellingPrice', 0))),
                total_amount=Decimal(str(pricing.get('totalPrice', 0))),
            )
            db.add(order_item)

    async def _update_order(self, db: AsyncSession, order: Order, flipkart_item: Dict):
        """Update existing order with Flipkart data"""
        order.status = self._map_flipkart_status(flipkart_item.get('state'))

    async def _create_product(self, db: AsyncSession, channel: Channel, listing: Dict):
        """Create product from Flipkart listing data"""
        from decimal import Decimal

        fsn = listing.get('fsn')
        sku = listing.get('sku')

        product = Product(
            tenant_id=channel.tenant_id,
            name=listing.get('title', ''),
            sku=sku,
            description=listing.get('description', ''),
            selling_price=Decimal(str(listing.get('sellingPrice', 0))),
            mrp=Decimal(str(listing.get('mrp', 0))),
            total_stock=0,  # Will be updated via inventory sync
            channel_mappings={str(channel.id): fsn},
        )
        db.add(product)

    async def _update_product(self, db: AsyncSession, product: Product, listing: Dict):
        """Update existing product with Flipkart listing data"""
        from decimal import Decimal

        product.name = listing.get('title', product.name)
        product.selling_price = Decimal(str(listing.get('sellingPrice', product.selling_price)))
        if listing.get('mrp'):
            product.mrp = Decimal(str(listing.get('mrp')))

    def _map_flipkart_status(self, flipkart_status: str) -> OrderStatus:
        """Map Flipkart order status to internal status"""
        status_map = {
            'APPROVED': OrderStatus.CONFIRMED,
            'PACKING_IN_PROGRESS': OrderStatus.PROCESSING,
            'READY_TO_DISPATCH': OrderStatus.PROCESSING,
            'SHIPPED': OrderStatus.SHIPPED,
            'DELIVERED': OrderStatus.DELIVERED,
            'CANCELLED': OrderStatus.CANCELLED,
            'RETURNED': OrderStatus.RTO_DELIVERED,
            'RETURN_REQUESTED': OrderStatus.RTO_IN_TRANSIT,
        }
        return status_map.get(flipkart_status, OrderStatus.PENDING)
