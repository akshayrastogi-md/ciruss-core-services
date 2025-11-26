"""
User and authentication models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
import enum
from app.models.base import BaseModel


class RoleType(str, enum.Enum):
    """User role types"""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    FINANCE = "finance"


class User(BaseModel):
    """User model"""

    __tablename__ = "users"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic Info
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    # Email Verification
    verification_token = Column(String(255), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Password Reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Login Tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")


class Role(BaseModel):
    """Role model"""

    __tablename__ = "roles"

    name = Column(SQLEnum(RoleType), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(Text, nullable=True)  # JSON string of permissions

    # Relationships
    user_roles = relationship("UserRole", back_populates="role")


class UserRole(BaseModel):
    """User-Role association"""

    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class APIKey(BaseModel):
    """API Key model"""

    __tablename__ = "api_keys"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)

    name = Column(String(255), nullable=False)
    key = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)  # First few chars for identification

    # Scope
    scope = Column(String(50), default="read-only")  # read-only, write, full-access

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Usage Tracking
    usage_count = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="api_keys")
