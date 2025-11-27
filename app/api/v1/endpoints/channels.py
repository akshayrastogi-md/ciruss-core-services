"""
Channels API endpoints - Complete CRUD implementation
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.channel import Channel, ChannelType, ChannelCredentials
from app.services.channels.factory import ChannelServiceFactory
from app.core.security import encrypt_data, decrypt_data
import json

router = APIRouter()


# Schemas
class ChannelCreate(BaseModel):
    """Channel creation schema"""
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: ChannelType
    store_url: Optional[str] = None
    credentials: dict  # Channel-specific credentials


class ChannelUpdate(BaseModel):
    """Channel update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    auto_sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    webhook_enabled: Optional[bool] = None


class ChannelResponse(BaseModel):
    """Channel response schema"""
    id: int
    name: str
    channel_type: ChannelType
    store_url: Optional[str]
    is_active: bool
    is_connected: bool
    last_sync_at: Optional[str]
    last_sync_status: Optional[str]
    auto_sync_enabled: bool
    sync_interval_minutes: int
    webhook_enabled: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# Background task for channel sync
async def sync_channel_task(db: AsyncSession, channel_id: int):
    """Background task to sync channel data"""
    from app.tasks.channel_tasks import sync_channel
    sync_channel.delay(channel_id)


# Endpoints
@router.post("/", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: ChannelCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create and connect a new channel
    """
    # Check subscription limits
    from app.services.razorpay_service import razorpay_service

    # Get current channels count
    result = await db.execute(
        select(Channel).where(
            and_(
                Channel.tenant_id == current_user.tenant_id,
                Channel.is_active == True,
            )
        )
    )
    active_channels = len(result.scalars().all())

    # Check limit
    usage_check = await razorpay_service.check_usage_limit(db, current_user.tenant_id)
    # TODO: Add channel limit check based on subscription plan

    # Test connection with credentials
    try:
        service = ChannelServiceFactory.create(channel_data.channel_type)
        is_authenticated = await service.authenticate(channel_data.credentials)

        if not is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with channel. Please check credentials.",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Channel authentication failed: {str(e)}",
        )

    # Create channel
    channel = Channel(
        tenant_id=current_user.tenant_id,
        name=channel_data.name,
        channel_type=channel_data.channel_type,
        store_url=channel_data.store_url,
        is_active=True,
        is_connected=True,
        last_sync_status="pending",
    )

    db.add(channel)
    await db.flush()

    # Encrypt and store credentials
    encrypted_credentials = encrypt_data(json.dumps(channel_data.credentials))

    credentials = ChannelCredentials(
        tenant_id=current_user.tenant_id,
        channel_id=channel.id,
        encrypted_credentials=encrypted_credentials,
    )

    db.add(credentials)
    await db.commit()
    await db.refresh(channel)

    # Trigger initial sync in background
    background_tasks.add_task(sync_channel_task, db, channel.id)

    return channel


@router.get("/", response_model=List[ChannelResponse])
async def list_channels(
    is_active: Optional[bool] = None,
    channel_type: Optional[ChannelType] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all channels
    """
    query = select(Channel).where(Channel.tenant_id == current_user.tenant_id)

    if is_active is not None:
        query = query.where(Channel.is_active == is_active)

    if channel_type:
        query = query.where(Channel.channel_type == channel_type)

    query = query.order_by(Channel.created_at.desc())

    result = await db.execute(query)
    channels = result.scalars().all()

    return channels


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific channel
    """
    result = await db.execute(
        select(Channel).where(
            and_(
                Channel.id == channel_id,
                Channel.tenant_id == current_user.tenant_id,
            )
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )

    return channel


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    channel_data: ChannelUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update channel settings
    """
    # Get channel
    result = await db.execute(
        select(Channel).where(
            and_(
                Channel.id == channel_id,
                Channel.tenant_id == current_user.tenant_id,
            )
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )

    # Update fields
    update_data = channel_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)

    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete (deactivate) a channel
    """
    # Get channel
    result = await db.execute(
        select(Channel).where(
            and_(
                Channel.id == channel_id,
                Channel.tenant_id == current_user.tenant_id,
            )
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )

    # Soft delete
    channel.is_active = False
    channel.is_connected = False
    await db.commit()


@router.post("/{channel_id}/sync")
async def trigger_sync(
    channel_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger channel synchronization
    """
    # Get channel
    result = await db.execute(
        select(Channel).where(
            and_(
                Channel.id == channel_id,
                Channel.tenant_id == current_user.tenant_id,
                Channel.is_active == True,
                Channel.is_connected == True,
            )
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found or not connected",
        )

    # Check if already syncing
    if channel.last_sync_status == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sync already in progress",
        )

    # Trigger sync
    background_tasks.add_task(sync_channel_task, db, channel.id)

    return {
        "channel_id": channel_id,
        "status": "sync_initiated",
        "message": "Channel sync has been triggered",
    }


@router.get("/{channel_id}/sync-status")
async def get_sync_status(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get channel sync status
    """
    # Get channel
    result = await db.execute(
        select(Channel).where(
            and_(
                Channel.id == channel_id,
                Channel.tenant_id == current_user.tenant_id,
            )
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )

    return {
        "channel_id": channel_id,
        "channel_name": channel.name,
        "last_sync_at": channel.last_sync_at.isoformat() if channel.last_sync_at else None,
        "last_sync_status": channel.last_sync_status,
        "is_connected": channel.is_connected,
        "auto_sync_enabled": channel.auto_sync_enabled,
        "sync_interval_minutes": channel.sync_interval_minutes,
    }


@router.post("/{channel_id}/test-connection")
async def test_connection(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test channel connection
    """
    # Get channel with credentials
    result = await db.execute(
        select(Channel).where(
            and_(
                Channel.id == channel_id,
                Channel.tenant_id == current_user.tenant_id,
            )
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )

    # Get credentials
    if not channel.credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel credentials not configured",
        )

    # Decrypt credentials
    decrypted = decrypt_data(channel.credentials.encrypted_credentials)
    credentials = json.loads(decrypted)

    # Test connection
    try:
        service = ChannelServiceFactory.create(channel.channel_type)
        is_connected = await service.authenticate(credentials)

        # Update channel
        channel.is_connected = is_connected
        await db.commit()

        return {
            "channel_id": channel_id,
            "is_connected": is_connected,
            "message": "Connection successful" if is_connected else "Connection failed",
            "tested_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "channel_id": channel_id,
            "is_connected": False,
            "message": f"Connection test failed: {str(e)}",
            "tested_at": datetime.utcnow().isoformat(),
        }


@router.get("/{channel_id}/stats")
async def get_channel_stats(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get channel statistics
    """
    from app.models.order import Order
    from app.models.product import Product
    from sqlalchemy import func

    # Get channel
    result = await db.execute(
        select(Channel).where(
            and_(
                Channel.id == channel_id,
                Channel.tenant_id == current_user.tenant_id,
            )
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )

    # Get order stats
    order_stats = await db.execute(
        select(
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_revenue'),
        ).where(Order.channel_id == channel_id)
    )
    stats = order_stats.first()

    # Get product count
    product_count = await db.execute(
        select(func.count(Product.id)).where(
            Product.channel_mappings.has_key(str(channel_id))
        )
    )

    return {
        "channel_id": channel_id,
        "channel_name": channel.name,
        "total_orders": stats.total_orders or 0,
        "total_revenue": float(stats.total_revenue or 0),
        "total_products": product_count.scalar() or 0,
        "is_connected": channel.is_connected,
        "created_at": channel.created_at.isoformat(),
    }
