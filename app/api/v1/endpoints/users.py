"""
Users endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import secrets

from app.core.deps import get_current_user, get_db
from app.core.security import hash_password
from app.models.user import User, Role, UserRole, APIKey
from app.schemas.user import (
    UserResponse,
    UserCreate,
    UserUpdate,
    UserRoleUpdate,
    APIKeyCreate,
    APIKeyResponse,
    RoleResponse,
)

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users in the tenant

    Returns all users belonging to the current tenant.
    """
    query = (
        select(User)
        .where(User.tenant_id == current_user.tenant_id)
        .limit(limit)
        .offset(offset)
        .order_by(User.created_at.desc())
    )

    result = await db.execute(query)
    users = result.scalars().all()

    # Get roles for each user
    user_responses = []
    for user in users:
        role_query = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
        role_result = await db.execute(role_query)
        roles = [row[0] for row in role_result.all()]

        user_responses.append(
            UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                phone=user.phone,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                roles=roles,
            )
        )

    return user_responses


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific user

    Returns details of a user by ID.
    """
    query = select(User).where(
        and_(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get roles
    role_query = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    role_result = await db.execute(role_query)
    roles = [row[0] for row in role_result.all()]

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        roles=roles,
    )


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user

    Creates a new user in the tenant with specified roles.
    """
    # Check if email already exists
    existing = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        tenant_id=current_user.tenant_id,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        is_active=True,
        is_verified=True,  # Admin-created users are auto-verified
    )

    db.add(user)
    await db.flush()

    # Assign roles
    if user_data.role_ids:
        for role_id in user_data.role_ids:
            user_role = UserRole(user_id=user.id, role_id=role_id)
            db.add(user_role)

    await db.commit()
    await db.refresh(user)

    # Get roles
    role_query = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    role_result = await db.execute(role_query)
    roles = [row[0] for row in role_result.all()]

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        roles=roles,
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user

    Updates user details (name, phone, active status).
    """
    query = select(User).where(
        and_(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    await db.commit()
    await db.refresh(user)

    # Get roles
    role_query = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    role_result = await db.execute(role_query)
    roles = [row[0] for row in role_result.all()]

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        roles=roles,
    )


@router.patch("/{user_id}/roles", response_model=UserResponse)
async def update_user_roles(
    user_id: int,
    role_data: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user roles

    Updates the roles assigned to a user.
    """
    query = select(User).where(
        and_(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Remove existing roles
    await db.execute(select(UserRole).where(UserRole.user_id == user_id))
    await db.execute(UserRole.__table__.delete().where(UserRole.user_id == user_id))

    # Add new roles
    for role_id in role_data.role_ids:
        user_role = UserRole(user_id=user.id, role_id=role_id)
        db.add(user_role)

    await db.commit()

    # Get roles
    role_query = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    role_result = await db.execute(role_query)
    roles = [row[0] for row in role_result.all()]

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        roles=roles,
    )


@router.get("/roles/", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
):
    """
    List all available roles

    Returns all system roles (Admin, Manager, Analyst, Finance).
    """
    query = select(Role)
    result = await db.execute(query)
    roles = result.scalars().all()

    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            slug=role.slug,
            description=role.description,
        )
        for role in roles
    ]


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an API key

    Generates a new API key for programmatic access.
    """
    # Generate API key
    key = f"d2c_live_{secrets.token_urlsafe(32)}"
    key_prefix = key[:12]  # Store only prefix for display

    api_key = APIKey(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        name=key_data.name,
        key_hash=hash_password(key),  # Hash the key
        key_prefix=key_prefix,
        scopes=key_data.scopes,
        is_active=True,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Return full key only on creation
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        api_key=key,  # Full key returned only here
    )


@router.get("/api-keys/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List API keys

    Returns all API keys for the current tenant.
    """
    query = select(APIKey).where(APIKey.tenant_id == current_user.tenant_id)
    result = await db.execute(query)
    api_keys = result.scalars().all()

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            scopes=key.scopes,
            is_active=key.is_active,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
            expires_at=key.expires_at,
        )
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke an API key

    Deactivates an API key.
    """
    query = select(APIKey).where(
        and_(APIKey.id == key_id, APIKey.tenant_id == current_user.tenant_id)
    )

    result = await db.execute(query)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await db.commit()

    return {"message": "API key revoked successfully"}
