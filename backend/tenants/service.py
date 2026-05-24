from __future__ import annotations

from sqlalchemy import select

from models import async_session
from tenants.models import Tenant


async def resolve_tenant(slug: str) -> Tenant | None:
    """Look up a tenant by slug. Returns None if not found."""
    async with async_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        return result.scalar_one_or_none()


async def update_tenant_config(tenant: Tenant, updates: dict) -> Tenant:
    """Merge *updates* into tenant.config JSONB field."""
    current = dict(tenant.config or {})
    _deep_merge(current, updates)

    async with async_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant.id)
        )
        db_tenant = result.scalar_one()
        db_tenant.config = current
        await db.commit()
        await db.refresh(db_tenant)

    return db_tenant


def _deep_merge(base: dict, updates: dict) -> None:
    """Recursive dict merge — mutates *base* in place."""
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
