"""
Shopify channel integration service - Complete Implementation
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
from app.core.security import encrypt_data, decrypt_data
from app.core.config import settings


class ShopifyService(BaseChannelService):
    """Shopify channel integration with OAuth and API support"""

    def __init__(self):
        self.api_version = settings.SHOPIFY_API_VERSION

    async def authenticate(self, credentials: Dict) -> bool:
        """Authenticate with Shopify using OAuth"""
        try:
            shop_url = credentials.get('shop_url')  # e.g., mystore.myshopify.com
            access_token = credentials.get('access_token')

            # Validate credentials by making a test API call
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{shop_url}/admin/api/{self.api_version}/shop.json",
                    headers={
                        "X-Shopify-Access-Token": access_token,
                        "Content-Type": "application/json",
                    }
                )

                return response.status_code == 200

        except Exception as e:
            print(f"Shopify authentication error: {e}")
            return False

    async def sync_orders(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync orders from Shopify
        Returns number of orders synced
        """
        # Decrypt credentials
        credentials = self._get_credentials(channel)

        if not credentials:
            raise ValueError("Channel credentials not found")

        shop_url = credentials['shop_url']
        access_token = credentials['access_token']

        # Get orders from Shopify (last 250, can be paginated)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{shop_url}/admin/api/{self.api_version}/orders.json",
                params={"limit": 250, "status": "any"},
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                }
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch Shopify orders: {response.text}")

            shopify_orders = response.json().get('orders', [])

        synced_count = 0

        for shopify_order in shopify_orders:
            # Check if order already exists
            external_order_id = str(shopify_order['id'])

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
                # Update existing order
                await self._update_order(db, existing_order, shopify_order)
            else:
                # Create new order
                await self._create_order(db, channel, shopify_order)
                synced_count += 1

        await db.commit()
        return synced_count

    async def sync_products(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync products from Shopify
        Returns number of products synced
        """
        credentials = self._get_credentials(channel)
        shop_url = credentials['shop_url']
        access_token = credentials['access_token']

        # Get products from Shopify
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{shop_url}/admin/api/{self.api_version}/products.json",
                params={"limit": 250},
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                }
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch Shopify products: {response.text}")

            shopify_products = response.json().get('products', [])

        synced_count = 0

        for shopify_product in shopify_products:
            external_product_id = str(shopify_product['id'])

            # Check channel mapping
            result = await db.execute(
                select(Product).where(
                    Product.channel_mappings.contains({str(channel.id): external_product_id})
                )
            )
            existing_product = result.scalar_one_or_none()

            if existing_product:
                # Update existing product
                await self._update_product(db, existing_product, shopify_product)
            else:
                # Create new product
                await self._create_product(db, channel, shopify_product)
                synced_count += 1

        await db.commit()
        return synced_count

    async def sync_inventory(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync inventory from Shopify
        Returns number of items synced
        """
        credentials = self._get_credentials(channel)
        shop_url = credentials['shop_url']
        access_token = credentials['access_token']

        # Get inventory levels from Shopify
        # First, get locations
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{shop_url}/admin/api/{self.api_version}/locations.json",
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                }
            )

            locations = response.json().get('locations', [])
            if not locations:
                return 0

            primary_location_id = locations[0]['id']

            # Get products to update inventory
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

            for product in products:
                external_product_id = product.channel_mappings.get(str(channel.id))

                # Get inventory for this product
                response = await client.get(
                    f"https://{shop_url}/admin/api/{self.api_version}/inventory_levels.json",
                    params={"location_ids": primary_location_id},
                    headers={
                        "X-Shopify-Access-Token": access_token,
                        "Content-Type": "application/json",
                    }
                )

                if response.status_code == 200:
                    inventory_levels = response.json().get('inventory_levels', [])
                    for level in inventory_levels:
                        # Update product stock
                        product.total_stock = level.get('available', 0)
                        synced_count += 1

            await db.commit()
            return synced_count

    async def create_order(self, db: AsyncSession, channel: Channel, order_data: Dict) -> Dict:
        """Create an order on Shopify"""
        credentials = self._get_credentials(channel)
        shop_url = credentials['shop_url']
        access_token = credentials['access_token']

        # Transform order data to Shopify format
        shopify_order = {
            "order": {
                "line_items": order_data.get('line_items', []),
                "customer": order_data.get('customer', {}),
                "billing_address": order_data.get('billing_address', {}),
                "shipping_address": order_data.get('shipping_address', {}),
                "financial_status": "pending",
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{shop_url}/admin/api/{self.api_version}/orders.json",
                json=shopify_order,
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                }
            )

            if response.status_code == 201:
                return response.json()
            else:
                raise Exception(f"Failed to create Shopify order: {response.text}")

    async def update_order_status(
        self,
        db: AsyncSession,
        channel: Channel,
        external_order_id: str,
        status: str,
    ) -> bool:
        """Update order status on Shopify"""
        credentials = self._get_credentials(channel)
        shop_url = credentials['shop_url']
        access_token = credentials['access_token']

        # Map internal status to Shopify fulfillment status
        fulfillment_data = {
            "fulfillment": {
                "location_id": None,  # Will be set from order
                "tracking_number": None,
                "notify_customer": True,
            }
        }

        async with httpx.AsyncClient() as client:
            if status == "fulfilled":
                response = await client.post(
                    f"https://{shop_url}/admin/api/{self.api_version}/orders/{external_order_id}/fulfillments.json",
                    json=fulfillment_data,
                    headers={
                        "X-Shopify-Access-Token": access_token,
                        "Content-Type": "application/json",
                    }
                )

                return response.status_code == 201
            else:
                # Update order
                update_data = {"order": {"tags": status}}

                response = await client.put(
                    f"https://{shop_url}/admin/api/{self.api_version}/orders/{external_order_id}.json",
                    json=update_data,
                    headers={
                        "X-Shopify-Access-Token": access_token,
                        "Content-Type": "application/json",
                    }
                )

                return response.status_code == 200

    def _get_credentials(self, channel: Channel) -> Dict:
        """Decrypt and return channel credentials"""
        if not channel.credentials or not channel.credentials.encrypted_credentials:
            raise ValueError("Channel credentials not configured")

        import json
        decrypted = decrypt_data(channel.credentials.encrypted_credentials)
        return json.loads(decrypted)

    async def _create_order(self, db: AsyncSession, channel: Channel, shopify_order: Dict):
        """Create order from Shopify data"""
        # Map Shopify order to internal Order model
        order = Order(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            order_number=shopify_order['order_number'],
            external_order_id=str(shopify_order['id']),
            order_date=datetime.fromisoformat(shopify_order['created_at'].replace('Z', '+00:00')),
            status=self._map_shopify_status(shopify_order['fulfillment_status']),
            customer_name=shopify_order.get('customer', {}).get('first_name', '') + ' ' + shopify_order.get('customer', {}).get('last_name', ''),
            customer_email=shopify_order.get('customer', {}).get('email'),
            customer_phone=shopify_order.get('customer', {}).get('phone', ''),
            shipping_address_line1=shopify_order.get('shipping_address', {}).get('address1', ''),
            shipping_city=shopify_order.get('shipping_address', {}).get('city', ''),
            shipping_state=shopify_order.get('shipping_address', {}).get('province', ''),
            shipping_pincode=shopify_order.get('shipping_address', {}).get('zip', ''),
            billing_address_line1=shopify_order.get('billing_address', {}).get('address1', ''),
            billing_city=shopify_order.get('billing_address', {}).get('city', ''),
            billing_state=shopify_order.get('billing_address', {}).get('province', ''),
            billing_pincode=shopify_order.get('billing_address', {}).get('zip', ''),
            payment_method=PaymentMethod.PREPAID if shopify_order.get('gateway') != 'Cash on Delivery (COD)' else PaymentMethod.COD,
            subtotal=float(shopify_order.get('subtotal_price', 0)),
            discount_amount=float(shopify_order.get('total_discounts', 0)),
            tax_amount=float(shopify_order.get('total_tax', 0)),
            total_amount=float(shopify_order.get('total_price', 0)),
        )

        db.add(order)
        await db.flush()

        # Add order items
        for line_item in shopify_order.get('line_items', []):
            order_item = OrderItem(
                tenant_id=channel.tenant_id,
                order_id=order.id,
                product_name=line_item.get('title', ''),
                sku=line_item.get('sku', ''),
                unit_price=float(line_item.get('price', 0)),
                quantity=line_item.get('quantity', 1),
                total_amount=float(line_item.get('price', 0)) * line_item.get('quantity', 1),
            )
            db.add(order_item)

    async def _update_order(self, db: AsyncSession, order: Order, shopify_order: Dict):
        """Update existing order with Shopify data"""
        order.status = self._map_shopify_status(shopify_order.get('fulfillment_status'))
        # Update other fields as needed

    async def _create_product(self, db: AsyncSession, channel: Channel, shopify_product: Dict):
        """Create product from Shopify data"""
        product = Product(
            tenant_id=channel.tenant_id,
            name=shopify_product.get('title', ''),
            sku=shopify_product.get('variants', [{}])[0].get('sku', ''),
            description=shopify_product.get('body_html', ''),
            selling_price=float(shopify_product.get('variants', [{}])[0].get('price', 0)),
            total_stock=shopify_product.get('variants', [{}])[0].get('inventory_quantity', 0),
            channel_mappings={str(channel.id): str(shopify_product['id'])},
        )
        db.add(product)

    async def _update_product(self, db: AsyncSession, product: Product, shopify_product: Dict):
        """Update existing product with Shopify data"""
        product.name = shopify_product.get('title', product.name)
        product.selling_price = float(shopify_product.get('variants', [{}])[0].get('price', product.selling_price))

    def _map_shopify_status(self, shopify_status: Optional[str]) -> OrderStatus:
        """Map Shopify fulfillment status to internal status"""
        status_map = {
            None: OrderStatus.PENDING,
            'fulfilled': OrderStatus.DELIVERED,
            'partial': OrderStatus.PROCESSING,
            'restocked': OrderStatus.CANCELLED,
        }
        return status_map.get(shopify_status, OrderStatus.PENDING)
