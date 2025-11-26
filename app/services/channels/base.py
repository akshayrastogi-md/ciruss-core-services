"""
Base channel service interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel


class BaseChannelService(ABC):
    """Base class for all channel integrations"""

    @abstractmethod
    async def authenticate(self, credentials: Dict) -> bool:
        """Authenticate with the channel"""
        pass

    @abstractmethod
    async def sync_orders(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync orders from the channel
        Returns number of orders synced
        """
        pass

    @abstractmethod
    async def sync_products(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync products from the channel
        Returns number of products synced
        """
        pass

    @abstractmethod
    async def sync_inventory(self, db: AsyncSession, channel: Channel) -> int:
        """
        Sync inventory from the channel
        Returns number of items synced
        """
        pass

    @abstractmethod
    async def create_order(self, db: AsyncSession, channel: Channel, order_data: Dict) -> Dict:
        """Create an order on the channel"""
        pass

    @abstractmethod
    async def update_order_status(
        self,
        db: AsyncSession,
        channel: Channel,
        external_order_id: str,
        status: str,
    ) -> bool:
        """Update order status on the channel"""
        pass
