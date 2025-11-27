"""
Base model with common fields
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, func
from sqlalchemy.ext.declarative import declared_attr
from app.db.session import Base


class BaseModel(Base):
    """Base model with common fields"""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def dict(self):
        """Convert model to dictionary"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TenantBaseModel(BaseModel):
    """Base model with multi-tenancy support"""

    __abstract__ = True

    @declared_attr
    def tenant_id(cls):
        return Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
