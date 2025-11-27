"""
User schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """User response schema"""

    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    roles: List[str] = []

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Create user schema"""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    role_ids: List[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Update user schema"""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserRoleUpdate(BaseModel):
    """Update user roles"""

    role_ids: List[int] = Field(..., min_items=1)


class APIKeyCreate(BaseModel):
    """Create API key"""

    name: str = Field(..., min_length=2, max_length=100)
    scopes: List[str] = Field(default_factory=lambda: ["read"])


class APIKeyResponse(BaseModel):
    """API key response"""

    id: int
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    # Only returned on creation
    api_key: Optional[str] = None

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Role response"""

    id: int
    name: str
    slug: str
    description: Optional[str] = None

    class Config:
        from_attributes = True
