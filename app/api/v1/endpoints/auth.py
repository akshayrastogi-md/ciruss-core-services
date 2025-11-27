"""
Authentication endpoints
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.db.redis import get_redis, RedisClient
from app.models.user import User, Role, UserRole, RoleType
from app.models.tenant import Tenant, TenantSettings
from app.schemas.auth import (
    UserLogin,
    UserRegister,
    TokenResponse,
    PasswordReset,
    PasswordResetConfirm,
    PasswordChange,
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    generate_verification_token,
    generate_reset_token,
)
from app.core.deps import get_current_user
from app.core.config import settings
from slugify import slugify

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Register a new user and create tenant
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create tenant
    tenant_slug = slugify(user_data.company_name)

    # Ensure unique slug
    base_slug = tenant_slug
    counter = 1
    while True:
        result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        if not result.scalar_one_or_none():
            break
        tenant_slug = f"{base_slug}-{counter}"
        counter += 1

    tenant = Tenant(
        name=user_data.company_name,
        slug=tenant_slug,
        email=user_data.email,
        gstin=user_data.gstin,
        is_active=True,
        is_verified=False,
    )
    db.add(tenant)
    await db.flush()

    # Create tenant settings
    tenant_settings = TenantSettings(tenant_id=tenant.id)
    db.add(tenant_settings)

    # Create user
    verification_token = generate_verification_token()
    user = User(
        tenant_id=tenant.id,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        is_active=True,
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(user)
    await db.flush()

    # Assign admin role
    result = await db.execute(select(Role).where(Role.name == RoleType.ADMIN))
    admin_role = result.scalar_one_or_none()

    if not admin_role:
        # Create admin role if it doesn't exist
        admin_role = Role(
            name=RoleType.ADMIN,
            display_name="Administrator",
            description="Full access to all features",
        )
        db.add(admin_role)
        await db.flush()

    user_role = UserRole(user_id=user.id, role_id=admin_role.id)
    db.add(user_role)

    # Create trial subscription
    from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, PlanType

    result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.name == PlanType.TRIAL))
    trial_plan = result.scalar_one_or_none()

    if trial_plan:
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_id=trial_plan.id,
            status=SubscriptionStatus.TRIALING,
            start_date=datetime.utcnow(),
            trial_end_date=datetime.utcnow() + timedelta(days=14),
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=14),
        )
        db.add(subscription)

    await db.commit()
    await db.refresh(user)

    # TODO: Send verification email
    # await send_verification_email(user.email, verification_token)

    # Create tokens
    access_token = create_access_token({"sub": user.id, "tenant_id": tenant.id})
    refresh_token = create_refresh_token({"sub": user.id, "tenant_id": tenant.id})

    # Store refresh token in Redis
    await redis.set(
        f"refresh_token:{user.id}",
        refresh_token,
        expire=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        db="session",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Login user
    """
    # Get user
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked due to too many failed login attempts",
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)

        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Reset failed attempts and update last login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Create tokens
    access_token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id})
    refresh_token = create_refresh_token({"sub": user.id, "tenant_id": user.tenant_id})

    # Store refresh token in Redis
    await redis.set(
        f"refresh_token:{user.id}",
        refresh_token,
        expire=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        db="session",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis),
):
    """
    Logout user (invalidate refresh token)
    """
    await redis.delete(f"refresh_token:{current_user.id}", db="session")
    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "is_verified": current_user.is_verified,
        "tenant_id": current_user.tenant_id,
    }
