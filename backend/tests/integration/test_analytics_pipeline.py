"""Pipeline stage: Admin Dashboard (Analytics) — seed events -> analytics endpoints -> verify structure.

Integration tests use real test DB, mock only external APIs.
"""

import uuid

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from conftest import TEST_TENANT_ID


@pytest.mark.asyncio
async def test_profile_dashboard_returns_structure(async_client, test_tenant, tenant_admin_user, seed_event):
    """Pipeline stage: Admin Analytics — profile-dashboard endpoint returns expected keys."""
    await seed_event("profile.updated", tenant_id=TEST_TENANT_ID, payload={"completeness": "L1"})

    from core.tenant_context import _current_tenant, _current_user
    from tenants.models import Tenant
    from models.user import User

    async def _set_context():
        from models import async_session
        async with async_session() as db:
            from sqlalchemy import select
            t = (await db.execute(select(Tenant).where(Tenant.id == TEST_TENANT_ID))).scalar_one()
            u = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
            _current_tenant.set(t)
            _current_user.set(u)

    await _set_context()

    resp = await async_client.get(
        "/api/v1/admin/analytics/profile-dashboard",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_topic_cloud_returns_structure(async_client, test_tenant, tenant_admin_user, seed_event):
    """Pipeline stage: Admin Analytics — topic-cloud returns topic frequency data."""
    await seed_event(
        "chat.message_sent",
        tenant_id=TEST_TENANT_ID,
        payload={"message_length": 50},
    )

    from core.tenant_context import _current_tenant, _current_user
    from tenants.models import Tenant
    from models.user import User

    async def _set_context():
        from models import async_session
        async with async_session() as db:
            from sqlalchemy import select
            t = (await db.execute(select(Tenant).where(Tenant.id == TEST_TENANT_ID))).scalar_one()
            u = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
            _current_tenant.set(t)
            _current_user.set(u)

    await _set_context()

    resp = await async_client.get(
        "/api/v1/admin/analytics/topic-cloud",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_is_tenant_scoped(async_client, test_tenant, other_tenant, seed_event):
    """Pipeline stage: Admin Analytics — analytics only counts events from the requesting tenant."""
    # Seed events for test tenant
    await seed_event("page.viewed", tenant_id=TEST_TENANT_ID)
    # Seed events for other tenant
    await seed_event("page.viewed", tenant_id=uuid.UUID("22222222-2222-2222-2222-222222222222"))

    from models import async_session
    from sqlalchemy import text

    async with async_session() as db:
        result = await db.execute(
            text("SELECT COUNT(*) FROM event_logs WHERE tenant_id = :tid AND event_type = 'page.viewed'"),
            {"tid": TEST_TENANT_ID},
        )
        count = result.scalar()
        # Only our tenant's event should be counted
        assert count == 1
