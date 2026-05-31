import asyncio
import importlib
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://gaokao:gaokao@db:5432/gaokao_test",
)
os.environ.setdefault("REDIS_URL", os.environ.get("TEST_REDIS_URL", "redis://redis:6379/15"))
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

TEST_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TEST_TENANT_SLUG = "test"
OTHER_TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

_schema_created = False


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    import models
    importlib.reload(models)
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    global _schema_created
    from models import Base, engine, async_session
    from models import admission, college, industry, mapping, profile, recommendation, recommendation_feedback, user  # noqa: F401
    from tenants import models as tenant_models  # noqa: F401

    if not _schema_created:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("DROP TABLE IF EXISTS event_logs CASCADE"))
            await conn.execute(
                text(
                    """
                    CREATE TABLE event_logs (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL,
                        event_type VARCHAR(64) NOT NULL,
                        user_id UUID,
                        session_id UUID,
                        payload JSONB NOT NULL DEFAULT '{}',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
        _schema_created = True

    # Ensure expires_at column exists (migration 006 may not have run on test DB)
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE consult_sessions ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ"
        ))

    yield

    await engine.dispose()

    async with async_session() as db:
        for table in ["event_logs", "session_profiles", "tenant_data", "tenant_users",
                       "departments", "tenants", "recommendation_feedback",
                       "recommendations", "user_profiles", "users",
                       "chat_messages", "consult_sessions", "admission_data", "colleges"]:
            try:
                await db.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass
        try:
            await db.commit()
        except Exception:
            await db.rollback()


@pytest.fixture
def tenant_config() -> dict[str, Any]:
    modules = {
        "funnel": True,
        "profile_dashboard": True,
        "major_heatmap": True,
        "region_distribution": True,
        "competitive_analysis": True,
        "dialogue_quality": True,
        "annual_report": True,
        "topic_cloud": True,
        "emotion_timeline": True,
        "hot_questions": True,
        "multi_department": True,
        "role_management": True,
    }
    return {
        "brand": {"name": "Test University", "short_name": "TestU", "primary_color": "#2563eb"},
        "modules": modules,
    }


@pytest_asyncio.fixture
async def test_tenant(tenant_config):
    from models import async_session
    from tenants.models import Tenant

    tenant = Tenant(
        id=TEST_TENANT_ID,
        name="Test University",
        slug=TEST_TENANT_SLUG,
        config=tenant_config,
        subscription_tier="advanced",
        status="active",
    )
    async with async_session() as db:
        db.add(tenant)
        await db.commit()
    return tenant


@pytest_asyncio.fixture
async def other_tenant(tenant_config):
    from models import async_session
    from tenants.models import Tenant

    tenant = Tenant(
        id=OTHER_TENANT_ID,
        name="Other University",
        slug="other",
        config=tenant_config,
        subscription_tier="basic",
        status="active",
    )
    async with async_session() as db:
        db.add(tenant)
        await db.commit()
    return tenant


@pytest_asyncio.fixture
async def tenant_admin_user(test_tenant):
    from models import async_session
    from models.user import User
    from tenants.models import TenantUser
    from utils.security import hash_password

    user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    tenant_user_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    async with async_session() as db:
        user = User(id=user_id, username="admin", password_hash=hash_password("admin123"))
        db.add(user)
        db.add(TenantUser(id=tenant_user_id, tenant_id=test_tenant.id, user_id=user_id, role="admin"))
        await db.commit()
    return {"user_id": user_id, "username": "admin"}


@pytest_asyncio.fixture
async def seed_event():
    from models import async_session

    async def _seed(
        event_type: str,
        *,
        tenant_id: uuid.UUID = TEST_TENANT_ID,
        user_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ):
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        if isinstance(session_id, str):
            session_id = uuid.UUID(session_id)

        async with async_session() as db:
            await db.execute(
                text(
                    """
                    INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                    VALUES (:id, :tenant_id, :event_type, :user_id, :session_id, CAST(:payload AS JSONB), :created_at)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "tenant_id": tenant_id,
                    "event_type": event_type,
                    "user_id": user_id or uuid.uuid4(),
                    "session_id": session_id or uuid.uuid4(),
                    "payload": __import__("json").dumps(payload or {}),
                    "created_at": created_at or datetime.now(timezone.utc),
                },
            )
            await db.commit()

    return _seed


@pytest_asyncio.fixture
async def seed_session_profile():
    from models import async_session
    from tenants.models import SessionProfile

    async def _seed(
        *,
        tenant_id: uuid.UUID = TEST_TENANT_ID,
        session_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        profile_json: dict[str, Any] | None = None,
        confidence_json: dict[str, Any] | None = None,
        completeness: str = "L1",
    ):
        async with async_session() as db:
            profile = SessionProfile(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                session_id=session_id or uuid.uuid4(),
                user_id=user_id,
                profile_json=profile_json or {},
                confidence_json=confidence_json or {},
                completeness=completeness,
            )
            db.add(profile)
            await db.commit()
        return profile

    return _seed


@asynccontextmanager
async def _noop_lifespan(app):
    yield


@pytest.fixture
def app_client(monkeypatch):
    from main import app

    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def async_client(monkeypatch):
    from main import app

    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
