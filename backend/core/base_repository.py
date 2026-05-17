"""Base repository that enforces tenant_id filtering on every query.

All per-tenant repositories inherit from this. The tenant_id filter is
mandatory — if your code path doesn't have a tenant, use a plain query.
"""
from __future__ import annotations

from sqlalchemy import select

from core.database import async_session
from core.tenant_context import get_current_tenant


class BaseRepository:
    model = None  # override in subclass

    @classmethod
    async def find_all(cls, **filters):
        tenant = get_current_tenant()
        filters["tenant_id"] = tenant.id
        async with async_session() as db:
            result = await db.execute(select(cls.model).filter_by(**filters))
            return result.scalars().all()

    @classmethod
    async def find_by_id(cls, id_):
        tenant = get_current_tenant()
        async with async_session() as db:
            result = await db.execute(
                select(cls.model).where(
                    cls.model.id == id_,
                    cls.model.tenant_id == tenant.id,
                )
            )
            return result.scalar_one_or_none()
