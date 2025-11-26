"""
Authentication schemas
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    """User login schema"""

    email: EmailStr
    password: str = Field(..., min_length=8)


class UserRegister(BaseModel):
    """User registration schema"""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    company_name: str = Field(..., min_length=2, max_length=255)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)


class TokenResponse(BaseModel):
    """Token response schema"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PasswordReset(BaseModel):
    """Password reset request schema"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""

    token: str
    new_password: str = Field(..., min_length=8)


class PasswordChange(BaseModel):
    """Password change schema"""

    old_password: str
    new_password: str = Field(..., min_length=8)
