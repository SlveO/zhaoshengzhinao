"""Starlette middleware for tenant resolution and module gating."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import HTTPException

from core.tenant_context import TENANT_PUBLIC_PATHS, TENANT_PUBLIC_PATH_SUFFIXES, set_current_tenant
from core.module_registry import MODULE_ROUTE_MAP, ModuleKey
from tenants.service import resolve_tenant


def _is_public_path(path: str) -> bool:
    """Check if a path is tenant-exempt (exact match or suffix match)."""
    if path in TENANT_PUBLIC_PATHS:
        return True
    if path.startswith("/docs") or path == "/openapi.json":
        return True
    return any(path.endswith(s) for s in TENANT_PUBLIC_PATH_SUFFIXES)


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Extract X-Tenant header → resolve → store in contextvar.

    Skips public paths (login, register, health) that don't require a tenant.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip tenant resolution for CORS preflight and public paths
        if request.method == "OPTIONS":
            return await call_next(request)
        if _is_public_path(request.url.path):
            return await call_next(request)

        slug = request.headers.get("X-Tenant")
        if not slug:
            # For admin routes, allow fallback to ?tenant= query param
            slug = request.query_params.get("tenant")

        if not slug:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "MISSING_TENANT", "message": "X-Tenant header required"}},
            )

        tenant = await resolve_tenant(slug)
        if not tenant or tenant.status != "active":
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "INVALID_TENANT", "message": f"Tenant '{slug}' not found or inactive"}},
            )

        set_current_tenant(tenant)
        return await call_next(request)


class UserAuthMiddleware(BaseHTTPMiddleware):
    """Decode JWT from Authorization header → find TenantUser → set contextvar.

    Runs AFTER TenantResolutionMiddleware (tenant is already set).
    Runs BEFORE ModuleGateMiddleware (module gate needs user role).
    Skips public paths (login, register, health).
    """

    async def dispatch(self, request: Request, call_next):
        from core.tenant_context import _current_user

        if _is_public_path(request.url.path):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return await call_next(request)  # optional auth — guest OK

        token = auth[7:]
        try:
            from utils.jwt import decode_token
            payload = decode_token(token)
            if payload:
                from core.tenant_context import set_current_jwt_payload
                set_current_jwt_payload(payload)
                from models import async_session
                from sqlalchemy import select
                from tenants.models import TenantUser as TUModel
                async with async_session() as db:
                    result = await db.execute(
                        select(TUModel).where(TUModel.user_id == payload["user_id"])
                    )
                    tu = result.scalar_one_or_none()
                    if tu:
                        _current_user.set(tu)
        except Exception:
            pass

        return await call_next(request)


class ModuleGateMiddleware(BaseHTTPMiddleware):
    """Module gate disabled per admin data overhaul spec §4.9. All modules always enabled."""

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)
