"""Starlette middleware for tenant resolution and module gating."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import HTTPException

from core.tenant_context import TENANT_PUBLIC_PATHS, set_current_tenant
from core.module_registry import MODULE_ROUTE_MAP, ModuleKey
from tenants.service import resolve_tenant


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Extract X-Tenant header → resolve → store in contextvar.

    Skips public paths (login, register, health) that don't require a tenant.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip tenant resolution for public paths
        if request.url.path in TENANT_PUBLIC_PATHS or request.url.path.startswith("/docs"):
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
        from core.tenant_context import TENANT_PUBLIC_PATHS, _current_user

        if request.url.path in TENANT_PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return await call_next(request)  # optional auth — guest OK

        token = auth[7:]
        try:
            from utils.jwt import decode_token
            payload = decode_token(token)
            if payload:
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
    """Check that the tenant has the required module enabled for admin analytics routes."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")

        # Only gate specific admin analytics paths
        module = None
        for prefix, mod in MODULE_ROUTE_MAP.items():
            if path.startswith(prefix):
                module = mod
                break

        if module is not None:
            from core.tenant_context import _current_tenant
            from core.module_registry import MODULE_DEPENDENCIES
            tenant = _current_tenant.get()
            if tenant:
                modules = (tenant.config or {}).get("modules", {})
                if not modules.get(module.value, False):
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": {
                                "code": "MODULE_DISABLED",
                                "message": f"Module '{module.value}' is not enabled for this tenant",
                            }
                        },
                    )
                for dep in MODULE_DEPENDENCIES.get(module, []):
                    if not modules.get(dep.value, False):
                        from fastapi.responses import JSONResponse
                        return JSONResponse(
                            status_code=403,
                            content={
                                "error": {
                                    "code": "MODULE_DEPENDENCY_MISSING",
                                    "message": f"Module '{module.value}' requires '{dep.value}' which is not enabled",
                                }
                            },
                        )

        return await call_next(request)
