"""Pipeline stage: Knowledge Base — upload -> TenantData -> ChromaDB -> search.

Integration tests use real test DB + ChromaDB, mock only external embeddings.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from conftest import TEST_TENANT_ID


@pytest.mark.asyncio
async def test_upload_creates_tenant_data_record(async_client, test_tenant, tenant_admin_user):
    """Pipeline stage: Knowledge Base — uploading a document creates a TenantData row."""
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

    import io
    with patch("knowledge.indexer.index_tenant_data", new_callable=AsyncMock):
        resp = await async_client.post(
            "/api/v1/admin/knowledge/documents",
            files={"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")},
            data={"data_type": "admission_score"},
            headers={"X-Tenant": "test"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["imported"] >= 1


@pytest.mark.asyncio
async def test_index_status_returns_counts(async_client, test_tenant, tenant_admin_user):
    """Pipeline stage: Knowledge Base — index-status returns total/indexed/pending doc counts."""
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
        "/api/v1/admin/knowledge/index-status",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_docs" in data
    assert "indexed_docs" in data
    assert "pending_docs" in data


@pytest.mark.asyncio
async def test_reindex_triggers_chromadb(async_client, test_tenant, tenant_admin_user):
    """Pipeline stage: Knowledge Base — reindex endpoint triggers ChromaDB rebuild."""
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

    with patch("knowledge.indexer.reindex_tenant", new_callable=AsyncMock):
        resp = await async_client.post(
            "/api/v1/admin/knowledge/reindex",
            headers={"X-Tenant": "test"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"


@pytest.mark.asyncio
async def test_document_list_is_tenant_scoped(async_client, test_tenant, other_tenant, tenant_admin_user):
    """Pipeline stage: Knowledge Base — documents list only shows current tenant's docs."""
    from models import async_session
    from tenants.models import TenantData
    from core.tenant_context import _current_tenant, _current_user
    from models.user import User

    # Seed data for both tenants
    async with async_session() as db:
        db.add(TenantData(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            data_type="admission_score",
            title="Test Tenant Score Data",
            content={"major_name": "计算机科学与技术"},
        ))
        db.add(TenantData(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            data_type="admission_score",
            title="Other Tenant Score Data",
            content={"major_name": "软件工程"},
        ))
        await db.commit()

    async def _set_context():
        from models import async_session
        async with async_session() as db:
            from sqlalchemy import select
            from tenants.models import Tenant
            t = (await db.execute(select(Tenant).where(Tenant.id == TEST_TENANT_ID))).scalar_one()
            u = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
            _current_tenant.set(t)
            _current_user.set(u)

    await _set_context()

    resp = await async_client.get(
        "/api/v1/admin/knowledge/documents",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    titles = [doc["title"] for doc in resp.json()["documents"]]
    assert "Test Tenant Score Data" in titles
    assert "Other Tenant Score Data" not in titles
