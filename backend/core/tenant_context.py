from contextvars import ContextVar
from typing import Optional

from fastapi import HTTPException


_current_tenant: ContextVar[Optional[object]] = ContextVar("tenant", default=None)
_current_user: ContextVar[Optional[object]] = ContextVar("user", default=None)
_current_jwt_payload: ContextVar[Optional[dict]] = ContextVar("jwt_payload", default=None)

# Routes that do not require a tenant header
TENANT_PUBLIC_PATHS = {
    "/api/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    # C-end miniapp routes use tenant_slug from request body, not X-Tenant header
    "/api/v1/miniapp/enter",
    "/api/v1/chat/messages",
    "/api/v1/student/profile",
    "/api/v1/recommendations",
    "/api/v1/majors/analysis",
}

# Paths that don't require tenant if they match a specific suffix.
# Used for token-gated routes with dynamic segments.
# e.g. /api/v1/distribution/files/{id}/download — authenticated by token, not tenant.
TENANT_PUBLIC_PATH_SUFFIXES = {"/download"}


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


def get_current_jwt_payload() -> dict | None:
    return _current_jwt_payload.get()


def set_current_jwt_payload(payload: dict | None) -> None:
    _current_jwt_payload.set(payload)
