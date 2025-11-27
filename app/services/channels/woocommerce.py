"""
WooCommerce channel integration service - Complete Implementation
"""
from typing import Dict, List, Optional
from datetime import datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.services.channels.base import BaseChannelService
from app.models.channel import Channel
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.product import Product
from app.core.security import decrypt_data


class WooCommerceService(BaseChannelService):
    """WooCommerce REST API integration"""

    def __init__(self):
        self.api_version = "wc/v3"

    async def authenticate(self, credentials: Dict) -> bool:
        """Authenticate with WooCommerce using consumer key/secret"""
        try:
            store_url = credentials.get('store_url')  # e.g., https://mystore.com
            consumer_key = credentials.get('consumer_key')
            consumer_secret = credentials.get('consumer_secret')

            # Test API connection
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{store_url}/wp-json/{self.api_version}/system_status",
                    auth=(consumer_key, consumer_secret),
                    timeout=10.0,
                )
                return response.status_code == 200

        except Exception as e:
            print(f"WooCommerce authentication error: {e}")
            return False

    async def sync_orders(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync orders from WooCommerce
        Returns number of orders synced
        """
        credentials = self._get_credentials(channel)
        store_url = credentials['store_url']
        consumer_key = credentials['consumer_key']
        consumer_secret = credentials['consumer_secret']

        synced_count = 0

        # Get orders from WooCommerce (last 100, paginated)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{store_url}/wp-json/{self.api_version}/orders",
                auth=(consumer_key, consumer_secret),
                params={"per_page": 100, "orderby": "date", "order": "desc"},
                timeout=30.0,
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch WooCommerce orders: {response.text}")

            wc_orders = response.json()

        for wc_order in wc_orders:
            external_order_id = str(wc_order['id'])

            # Check if order exists
            result = await db.execute(
                select(Order).where(
                    and_(
                        Order.channel_id == channel.id,
                        Order.external_order_id == external_order_id,
                    )
                )
            )
            existing_order = result.scalar_one_or_none()

            if existing_order:
                await self._update_order(db, existing_order, wc_order)
            else:
                await self._create_order(db, channel, wc_order)
                synced_count += 1

        await db.commit()
        return synced_count

    async def sync_products(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync products from WooCommerce
        Returns number of products synced
        """
        credentials = self._get_credentials(channel)
        store_url = credentials['store_url']
        consumer_key = credentials['consumer_key']
        consumer_secret = credentials['consumer_secret']

        synced_count = 0

        # Get products from WooCommerce
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{store_url}/wp-json/{self.api_version}/products",
                auth=(consumer_key, consumer_secret),
                params={"per_page": 100},
                timeout=30.0,
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch WooCommerce products: {response.text}")

            wc_products = response.json()

        for wc_product in wc_products:
            external_product_id = str(wc_product['id'])

            # Check if product exists
            result = await db.execute(
                select(Product).where(
                    Product.channel_mappings.contains({str(channel.id): external_product_id})
                )
            )
            existing_product = result.scalar_one_or_none()

            if existing_product:
                await self._update_product(db, existing_product, wc_product)
            else:
                await self._create_product(db, channel, wc_product)
                synced_count += 1

        await db.commit()
        return synced_count

    async def sync_inventory(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync inventory from WooCommerce
        Returns number of items synced
        """
        credentials = self._get_credentials(channel)
        store_url = credentials['store_url']
        consumer_key = credentials['consumer_key']
        consumer_secret = credentials['consumer_secret']

        # Get products with stock info
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

        async with httpx.AsyncClient() as client:
            for product in products:
                external_product_id = product.channel_mappings.get(str(channel.id))

                # Get product stock info
                response = await client.get(
                    f"{store_url}/wp-json/{self.api_version}/products/{external_product_id}",
                    auth=(consumer_key, consumer_secret),
                    timeout=10.0,
                )

                if response.status_code == 200:
                    wc_product = response.json()
                    product.total_stock = wc_product.get('stock_quantity', 0)
                    synced_count += 1

        await db.commit()
        return synced_count

    async def create_order(self, db: AsyncSession, channel: Channel, order_data: Dict) -> Dict:
        """Create an order on WooCommerce"""
        credentials = self._get_credentials(channel)
        store_url = credentials['store_url']
        consumer_key = credentials['consumer_key']
        consumer_secret = credentials['consumer_secret']

        # Transform order data to WooCommerce format
        wc_order = {
            "payment_method": order_data.get('payment_method', 'cod'),
            "payment_method_title": order_data.get('payment_method_title', 'Cash on Delivery'),
            "set_paid": order_data.get('set_paid', False),
            "billing": order_data.get('billing', {}),
            "shipping": order_data.get('shipping', {}),
            "line_items": order_data.get('line_items', []),
            "shipping_lines": order_data.get('shipping_lines', []),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{store_url}/wp-json/{self.api_version}/orders",
                auth=(consumer_key, consumer_secret),
                json=wc_order,
                timeout=30.0,
            )

            if response.status_code == 201:
                return response.json()
            else:
                raise Exception(f"Failed to create WooCommerce order: {response.text}")

    async def update_order_status(
        self,
        db: AsyncSession,
        channel: Channel,
        external_order_id: str,
        status: str,
    ) -> bool:
        """Update order status on WooCommerce"""
        credentials = self._get_credentials(channel)
        store_url = credentials['store_url']
        consumer_key = credentials['consumer_key']
        consumer_secret = credentials['consumer_secret']

        # Map internal status to WooCommerce status
        status_map = {
            "pending": "pending",
            "processing": "processing",
            "completed": "completed",
            "cancelled": "cancelled",
            "refunded": "refunded",
            "failed": "failed",
        }

        wc_status = status_map.get(status, "processing")

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{store_url}/wp-json/{self.api_version}/orders/{external_order_id}",
                auth=(consumer_key, consumer_secret),
                json={"status": wc_status},
                timeout=30.0,
            )

            return response.status_code == 200

    def _get_credentials(self, channel: Channel) -> Dict:
        """Decrypt and return channel credentials"""
        if not channel.credentials or not channel.credentials.encrypted_credentials:
            raise ValueError("Channel credentials not configured")

        import json
        decrypted = decrypt_data(channel.credentials.encrypted_credentials)
        return json.loads(decrypted)

    async def _create_order(self, db: AsyncSession, channel: Channel, wc_order: Dict):
        """Create order from WooCommerce data"""
        from decimal import Decimal

        # Map payment method
        payment_method = PaymentMethod.COD if wc_order.get('payment_method') == 'cod' else PaymentMethod.PREPAID

        # Create order
        order = Order(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            order_number=wc_order['number'],
            external_order_id=str(wc_order['id']),
            order_date=datetime.fromisoformat(wc_order['date_created'].replace('T', ' ').split('.')[0]),
            status=self._map_wc_status(wc_order['status']),
            customer_name=f"{wc_order['billing']['first_name']} {wc_order['billing']['last_name']}",
            customer_email=wc_order['billing'].get('email'),
            customer_phone=wc_order['billing'].get('phone', ''),
            shipping_address_line1=wc_order['shipping'].get('address_1', ''),
            shipping_address_line2=wc_order['shipping'].get('address_2', ''),
            shipping_city=wc_order['shipping'].get('city', ''),
            shipping_state=wc_order['shipping'].get('state', ''),
            shipping_pincode=wc_order['shipping'].get('postcode', ''),
            billing_address_line1=wc_order['billing'].get('address_1', ''),
            billing_address_line2=wc_order['billing'].get('address_2', ''),
            billing_city=wc_order['billing'].get('city', ''),
            billing_state=wc_order['billing'].get('state', ''),
            billing_pincode=wc_order['billing'].get('postcode', ''),
            payment_method=payment_method,
            subtotal=Decimal(str(wc_order.get('total', 0))) - Decimal(str(wc_order.get('total_tax', 0))),
            discount_amount=Decimal(str(wc_order.get('discount_total', 0))),
            tax_amount=Decimal(str(wc_order.get('total_tax', 0))),
            shipping_charges=Decimal(str(wc_order.get('shipping_total', 0))),
            total_amount=Decimal(str(wc_order.get('total', 0))),
        )

        db.add(order)
        await db.flush()

        # Add order items
        for line_item in wc_order.get('line_items', []):
            order_item = OrderItem(
                tenant_id=channel.tenant_id,
                order_id=order.id,
                product_name=line_item.get('name', ''),
                sku=line_item.get('sku', ''),
                unit_price=Decimal(str(line_item.get('price', 0))),
                quantity=line_item.get('quantity', 1),
                tax_amount=Decimal(str(line_item.get('total_tax', 0))),
                total_amount=Decimal(str(line_item.get('total', 0))),
            )
            db.add(order_item)

    async def _update_order(self, db: AsyncSession, order: Order, wc_order: Dict):
        """Update existing order with WooCommerce data"""
        order.status = self._map_wc_status(wc_order.get('status'))

    async def _create_product(self, db: AsyncSession, channel: Channel, wc_product: Dict):
        """Create product from WooCommerce data"""
        from decimal import Decimal

        product = Product(
            tenant_id=channel.tenant_id,
            name=wc_product.get('name', ''),
            sku=wc_product.get('sku', ''),
            description=wc_product.get('description', ''),
            category=wc_product.get('categories', [{}])[0].get('name') if wc_product.get('categories') else None,
            selling_price=Decimal(str(wc_product.get('price', 0))),
            mrp=Decimal(str(wc_product.get('regular_price', 0))) if wc_product.get('regular_price') else None,
            total_stock=wc_product.get('stock_quantity', 0),
            weight=Decimal(str(wc_product.get('weight', 0))) if wc_product.get('weight') else None,
            image_url=wc_product.get('images', [{}])[0].get('src') if wc_product.get('images') else None,
            channel_mappings={str(channel.id): str(wc_product['id'])},
        )
        db.add(product)

    async def _update_product(self, db: AsyncSession, product: Product, wc_product: Dict):
        """Update existing product with WooCommerce data"""
        from decimal import Decimal

        product.name = wc_product.get('name', product.name)
        product.selling_price = Decimal(str(wc_product.get('price', product.selling_price)))
        product.total_stock = wc_product.get('stock_quantity', product.total_stock)

    def _map_wc_status(self, wc_status: str) -> OrderStatus:
        """Map WooCommerce status to internal status"""
        status_map = {
            'pending': OrderStatus.PENDING,
            'processing': OrderStatus.PROCESSING,
            'on-hold': OrderStatus.PENDING,
            'completed': OrderStatus.DELIVERED,
            'cancelled': OrderStatus.CANCELLED,
            'refunded': OrderStatus.CANCELLED,
            'failed': OrderStatus.CANCELLED,
        }
        return status_map.get(wc_status, OrderStatus.PENDING)
