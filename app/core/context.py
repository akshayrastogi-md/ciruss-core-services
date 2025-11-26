"""
Context management for multi-tenancy
"""
from contextvars import ContextVar
from typing import Optional

# Tenant context variable
_tenant_id: ContextVar[Optional[int]] = ContextVar("tenant_id", default=None)


class TenantContext:
    """Tenant context manager"""

    @staticmethod
    def set(tenant_id: int):
        """Set current tenant ID"""
        _tenant_id.set(tenant_id)

    @staticmethod
    def get() -> Optional[int]:
        """Get current tenant ID"""
        return _tenant_id.get()

    @staticmethod
    def clear():
        """Clear tenant context"""
        _tenant_id.set(None)


# Global tenant context instance
tenant_context = TenantContext()
