"""
Multi-tenancy middleware
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.context import tenant_context


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle multi-tenancy context
    """

    async def dispatch(self, request: Request, call_next):
        # Clear tenant context before each request
        tenant_context.clear()

        response = await call_next(request)

        # Clear tenant context after response
        tenant_context.clear()

        return response
