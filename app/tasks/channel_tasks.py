"""
Celery tasks for channel synchronization
"""
from celery import shared_task
from sqlalchemy import select
from app.tasks.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.channel import Channel


@celery_app.task(name="app.tasks.channel_tasks.sync_all_channels")
def sync_all_channels():
    """
    Sync all active channels
    """
    import asyncio
    asyncio.run(_sync_all_channels_async())


async def _sync_all_channels_async():
    """
    Async implementation of sync all channels
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Channel).where(
                Channel.is_active == True,
                Channel.is_connected == True,
                Channel.auto_sync_enabled == True,
            )
        )
        channels = result.scalars().all()

        for channel in channels:
            # Trigger individual channel sync
            sync_channel.delay(channel.id)


@celery_app.task(
    name="app.tasks.channel_tasks.sync_channel",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def sync_channel(self, channel_id: int):
    """
    Sync a specific channel
    """
    import asyncio
    try:
        asyncio.run(_sync_channel_async(channel_id))
    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc)


async def _sync_channel_async(channel_id: int):
    """
    Async implementation of channel sync
    """
    from datetime import datetime
    from app.services.channels.factory import ChannelServiceFactory

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = result.scalar_one_or_none()

        if not channel:
            return

        try:
            # Update sync status
            channel.last_sync_status = "in_progress"
            await db.commit()

            # Get channel service
            service = ChannelServiceFactory.create(channel.channel_type)

            # Sync orders
            await service.sync_orders(db, channel)

            # Sync products
            await service.sync_products(db, channel)

            # Sync inventory
            await service.sync_inventory(db, channel)

            # Update sync status
            channel.last_sync_at = datetime.utcnow()
            channel.last_sync_status = "success"
            await db.commit()

        except Exception as e:
            channel.last_sync_status = "failed"
            await db.commit()
            raise
