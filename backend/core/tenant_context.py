from contextvars import ContextVar
from typing import Optional

from fastapi import HTTPException


_current_tenant: ContextVar[Optional[object]] = ContextVar("tenant", default=None)
_current_user: ContextVar[Optional[object]] = ContextVar("user", default=None)

# Routes that do not require a tenant header
TENANT_PUBLIC_PATHS = {
    "/api/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/distribution/files",  # Token-gated file download, no tenant header needed
}


def get_current_tenant():
    """FastAPI dependency injection — returns the resolved Tenant or raises 401."""
    tenant = _current_tenant.get()
    if not tenant:
        raise HTTPException(status_code=401, detail="Tenant not resolved")
    return tenant


def get_current_tenant_user():
    """FastAPI dependency injection — for admin endpoints requiring login."""
    user = _current_user.get()
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def set_current_tenant(tenant):
    _current_tenant.set(tenant)


def set_current_user(user):
    _current_user.set(user)
