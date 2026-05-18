import io
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.tenant_context import _current_tenant, _current_user


class MockTenant:
    id = "t-1"
    name = "Test University"
    slug = "test"
    config = {}
    subscription_tier = "basic"
    status = "active"


class MockUser:
    id = "u-1"
    tenant_id = "t-1"
    role = "admin"


@asynccontextmanager
async def _noop_lifespan(app):
    yield


@pytest.fixture
def client(monkeypatch):
    from main import app
    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def override_deps(monkeypatch):
    from core import middleware as mw
    monkeypatch.setattr(mw, "resolve_tenant", AsyncMock(return_value=MockTenant()))
    _current_tenant.set(MockTenant())
    _current_user.set(MockUser())
    from main import app
    app.dependency_overrides = {}
    yield
    _current_tenant.set(None)
    _current_user.set(None)
    from main import app
    app.dependency_overrides = {}


def _make_db_mock(execute_return=None, execute_side_effect=None):
    """Create a mock DB session: execute is async, other methods are sync MagicMock."""
    db = MagicMock()
    db.execute = AsyncMock(return_value=execute_return, side_effect=execute_side_effect)
    return db


class TestKnowledgeEndpoints:

    def test_list_documents_returns_list(self, client):
        with patch("models.async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db = _make_db_mock(execute_return=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            resp = client.get("/api/v1/admin/knowledge/documents",
                              headers={"X-Tenant": "test"})
            assert resp.status_code == 200
            data = resp.json()
            assert "documents" in data

    def test_upload_excel_document(self, client):
        with patch("data.onboarding.excel_importer.import_excel", new_callable=AsyncMock) as mock_import:
            mock_import.return_value = {
                "success": True, "imported": 2, "errors": [], "total_rows": 2
            }
            excel_content = b"fake excel bytes"
            resp = client.post(
                "/api/v1/admin/knowledge/documents",
                files={"file": ("test.xlsx", io.BytesIO(excel_content),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"data_type": "admission_score"},
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["imported"] == 2

    def test_delete_document_not_found(self, client):
        with patch("models.async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db = _make_db_mock(execute_return=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            resp = client.delete(
                "/api/v1/admin/knowledge/documents/some-uuid",
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 404

    def test_reindex(self, client):
        with patch("knowledge.indexer.reindex_tenant", new_callable=AsyncMock):
            resp = client.post(
                "/api/v1/admin/knowledge/reindex",
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "started"

    def test_index_status(self, client):
        with patch("models.async_session") as mock_session:
            mock_result1 = MagicMock()
            mock_result1.scalar.return_value = 10
            mock_result2 = MagicMock()
            mock_result2.scalar.return_value = 8
            mock_db = _make_db_mock(execute_side_effect=[mock_result1, mock_result2])
            mock_session.return_value.__aenter__.return_value = mock_db

            resp = client.get(
                "/api/v1/admin/knowledge/index-status",
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_docs"] == 10
            assert data["indexed_docs"] == 8
            assert data["pending_docs"] == 2
