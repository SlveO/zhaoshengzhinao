"""Pipeline stage: Module Gating — enable/disable module -> 200/403 on analytics endpoints.

Integration tests use real test DB + middleware chain, mock only external APIs.
"""

import uuid
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from conftest import TEST_TENANT_ID


@pytest.mark.asyncio
async def test_enabled_module_returns_200(async_client, test_tenant, tenant_admin_user, seed_event):
    """Pipeline stage: Module Gating — enabled module allows access (200)."""
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
        "/api/v1/admin/analytics/funnel",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_disabled_module_returns_403(async_client, tenant_admin_user):
    """Pipeline stage: Module Gating — disabled module blocks access (403)."""
    from models import async_session
    from tenants.models import Tenant
    from core.tenant_context import _current_tenant, _current_user
    from models.user import User

    # Create tenant with funnel disabled
    config = {
        "brand": {"name": "NoFunnel U", "short_name": "NFU", "primary_color": "#000"},
        "modules": {
            "funnel": False,
            "profile_dashboard": True,
            "major_heatmap": True,
            "region_distribution": True,
            "competitive_analysis": True,
            "dialogue_quality": True,
            "annual_report": True,
            "topic_cloud": True,
            "emotion_timeline": True,
            "hot_questions": True,
        },
    }
    tenant_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    async with async_session() as db:
        t = Tenant(
            id=tenant_id,
            name="NoFunnel University",
            slug="nofunnel",
            config=config,
            subscription_tier="basic",
            status="active",
        )
        db.add(t)
        await db.commit()
        _current_tenant.set(t)

    async with async_session() as db:
        from sqlalchemy import select
        u = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
        _current_user.set(u)

    resp = await async_client.get(
        "/api/v1/admin/analytics/funnel",
        headers={"X-Tenant": "nofunnel"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_dependency_module_missing_returns_403(async_client, tenant_admin_user):
    """Pipeline stage: Module Gating — module with missing dependency returns 403."""
    from models import async_session
    from tenants.models import Tenant
    from core.tenant_context import _current_tenant, _current_user
    from models.user import User

    # competitive_analysis enabled but funnel (dependency) disabled
    config = {
        "brand": {"name": "DepTest U", "short_name": "DTU", "primary_color": "#000"},
        "modules": {
            "funnel": False,
            "profile_dashboard": True,
            "competitive_analysis": True,
            "major_heatmap": False,
            "region_distribution": True,
            "dialogue_quality": True,
            "annual_report": False,
            "topic_cloud": True,
            "emotion_timeline": True,
            "hot_questions": True,
        },
    }
    tenant_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    async with async_session() as db:
        t = Tenant(
            id=tenant_id,
            name="DepTest University",
            slug="deptest",
            config=config,
            subscription_tier="basic",
            status="active",
        )
        db.add(t)
        await db.commit()
        _current_tenant.set(t)

    async with async_session() as db:
        from sqlalchemy import select
        u = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
        _current_user.set(u)

    resp = await async_client.get(
        "/api/v1/admin/analytics/competitive",
        headers={"X-Tenant": "deptest"},
    )
    assert resp.status_code == 403
    assert "funnel" in resp.json()["error"]["message"].lower() or "requires" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_all_insights_modules_enabled(async_client, test_tenant, tenant_admin_user):
    """Pipeline stage: Module Gating — all insights modules (topic_cloud, emotion, hot_questions) return 200."""
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

    for endpoint in ["topic-cloud", "emotion-timeline", "hot-questions"]:
        resp = await async_client.get(
            f"/api/v1/admin/analytics/{endpoint}",
            headers={"X-Tenant": "test"},
        )
        assert resp.status_code == 200, f"{endpoint} returned {resp.status_code}"
