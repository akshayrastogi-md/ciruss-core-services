"""
Channel service factory
"""
from app.models.channel import ChannelType
from app.services.channels.base import BaseChannelService


class ChannelServiceFactory:
    """Factory for creating channel services"""

    @staticmethod
    def create(channel_type: ChannelType) -> BaseChannelService:
        """
        Create a channel service based on type
        """
        if channel_type == ChannelType.SHOPIFY:
            from app.services.channels.shopify import ShopifyService
            return ShopifyService()
        elif channel_type == ChannelType.WOOCOMMERCE:
            from app.services.channels.woocommerce import WooCommerceService
            return WooCommerceService()
        elif channel_type == ChannelType.AMAZON:
            from app.services.channels.amazon import AmazonService
            return AmazonService()
        elif channel_type == ChannelType.FLIPKART:
            from app.services.channels.flipkart import FlipkartService
            return FlipkartService()
        else:
            raise ValueError(f"Unsupported channel type: {channel_type}")
