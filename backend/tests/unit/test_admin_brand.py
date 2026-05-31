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
    yield
    _current_tenant.set(None)
    _current_user.set(None)
    app.dependency_overrides.clear()


class TestBrandEndpoints:

    # ── Upload logo ──

    def test_upload_logo_png(self, client):
        with patch("os.makedirs"), \
             patch("builtins.open"), \
             patch("os.path.exists", return_value=True):
            resp = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("logo.png", io.BytesIO(b"png content"), "image/png")},
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "logo_url" in data
            assert data["logo_url"].endswith(".png")

    def test_upload_logo_jpeg(self, client):
        with patch("os.makedirs"), \
             patch("builtins.open"), \
             patch("os.path.exists", return_value=True):
            resp = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("logo.jpeg", io.BytesIO(b"jpeg content"), "image/jpeg")},
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["logo_url"].endswith(".jpg") or data["logo_url"].endswith(".jpeg")

    def test_upload_favicon(self, client):
        with patch("os.makedirs"), \
             patch("builtins.open"), \
             patch("os.path.exists", return_value=True):
            resp = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("favicon.ico", io.BytesIO(b"ico content"), "image/x-icon")},
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["logo_url"].endswith(".ico")

    def test_upload_login_bg(self, client):
        with patch("os.makedirs"), \
             patch("builtins.open"), \
             patch("os.path.exists", return_value=True):
            resp = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("login-bg.jpg", io.BytesIO(b"bg content"), "image/jpeg")},
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "logo_url" in data

    def test_upload_creates_directory_if_missing(self, client):
        with patch("os.path.exists", return_value=False) as mock_exists, \
             patch("os.makedirs") as mock_makedirs, \
             patch("builtins.open"):
            resp = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("logo.png", io.BytesIO(b"png content"), "image/png")},
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            mock_makedirs.assert_called_once()

    def test_upload_preserves_file_extension(self, client):
        with patch("os.makedirs"), \
             patch("builtins.open"), \
             patch("os.path.exists", return_value=True):
            resp = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("logo.gif", io.BytesIO(b"gif content"), "image/gif")},
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            assert resp.json()["logo_url"].endswith(".gif")

    def test_upload_with_special_chars_in_filename(self, client):
        with patch("os.makedirs"), \
             patch("builtins.open"), \
             patch("os.path.exists", return_value=True):
            resp = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("招生Logo_v1.png", io.BytesIO(b"content"), "image/png")},
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert ".png" in data["logo_url"]

    def test_upload_without_file(self, client):
        resp = client.post(
            "/api/v1/admin/brand-config/logo",
            headers={"X-Tenant": "test"},
        )
        assert resp.status_code == 422

    def test_upload_without_auth(self, client):
        _current_user.set(None)
        resp = client.post(
            "/api/v1/admin/brand-config/logo",
            files={"file": ("logo.png", io.BytesIO(b"content"), "image/png")},
            headers={"X-Tenant": "test"},
        )
        assert resp.status_code == 401

    def test_upload_to_nonexistent_tenant(self, client, monkeypatch):
        from core import middleware as mw
        monkeypatch.setattr(mw, "resolve_tenant", AsyncMock(return_value=None))
        _current_tenant.set(None)
        resp = client.post(
            "/api/v1/admin/brand-config/logo",
            files={"file": ("logo.png", io.BytesIO(b"content"), "image/png")},
            headers={"X-Tenant": "test"},
        )
        assert resp.status_code == 401

    # ── Get brand config ──

    def test_get_brand_config(self, client, monkeypatch):
        brand = {
            "name": "华南师范大学",
            "short_name": "华师",
            "primary_color": "#1a56db",
            "logo_url": "/uploads/scnu/logo.png",
        }
        tenant = MockTenant()
        tenant.config = {"brand": brand}
        from core import middleware as mw
        monkeypatch.setattr(mw, "resolve_tenant", AsyncMock(return_value=tenant))
        _current_tenant.set(tenant)

        resp = client.get(
            "/api/v1/admin/brand-config",
            headers={"X-Tenant": "test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "华南师范大学"
        assert data["primary_color"] == "#1a56db"

    def test_get_brand_config_empty(self, client):
        tenant = MockTenant()
        tenant.config = {}
        from core.tenant_context import get_current_tenant
        from main import app
        app.dependency_overrides[get_current_tenant] = lambda: tenant

        resp = client.get(
            "/api/v1/admin/brand-config",
            headers={"X-Tenant": "test"},
        )
        assert resp.status_code == 200
        assert resp.json() == {}

    # ── Update brand config ──

    def test_update_brand_config(self, client):
        updated_brand = {
            "name": "华师",
            "short_name": "SCNU",
            "primary_color": "#ff0000",
            "secondary_color": "#00ff00",
            "logo_url": "/uploads/scnu/logo.png",
            "welcome_text": "Welcome",
        }
        tenant = MockTenant()
        from core.tenant_context import get_current_tenant
        from main import app
        app.dependency_overrides[get_current_tenant] = lambda: tenant
        with patch("tenants.service.update_tenant_config", new_callable=AsyncMock) as mock_update:
            merged_tenant = MockTenant()
            merged_tenant.config = {"brand": updated_brand}
            mock_update.return_value = merged_tenant

            resp = client.put(
                "/api/v1/admin/brand-config",
                json=updated_brand,
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "华师"
            assert data["primary_color"] == "#ff0000"
            mock_update.assert_called_once()

    def test_update_brand_config_partial(self, client):
        partial = {"primary_color": "#000000"}
        merged_brand = {"name": "Test University", "primary_color": "#000000"}
        tenant = MockTenant()
        from core.tenant_context import get_current_tenant
        from main import app
        app.dependency_overrides[get_current_tenant] = lambda: tenant
        with patch("tenants.service.update_tenant_config", new_callable=AsyncMock) as mock_update:
            merged_tenant = MockTenant()
            merged_tenant.config = {"brand": merged_brand}
            mock_update.return_value = merged_tenant

            resp = client.put(
                "/api/v1/admin/brand-config",
                json=partial,
                headers={"X-Tenant": "test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["primary_color"] == "#000000"

    # ── Tenant isolation ──

    def test_different_tenants_separate_urls(self, client, monkeypatch):
        """Upload same filename to two tenants -> logo_urls differ by slug."""
        from core import middleware as mw
        from core.tenant_context import _current_tenant

        with patch("os.makedirs"), \
             patch("builtins.open"), \
             patch("os.path.exists", return_value=True):

            # Tenant A (scnu)
            tenant_a = MockTenant()
            tenant_a.slug = "scnu"
            monkeypatch.setattr(mw, "resolve_tenant", AsyncMock(return_value=tenant_a))
            _current_tenant.set(tenant_a)
            resp_a = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("logo.png", io.BytesIO(b"png"), "image/png")},
                headers={"X-Tenant": "scnu"},
            )
            url_a = resp_a.json()["logo_url"]

            # Tenant B (sysu)
            tenant_b = MockTenant()
            tenant_b.slug = "sysu"
            monkeypatch.setattr(mw, "resolve_tenant", AsyncMock(return_value=tenant_b))
            _current_tenant.set(tenant_b)
            resp_b = client.post(
                "/api/v1/admin/brand-config/logo",
                files={"file": ("logo.png", io.BytesIO(b"png"), "image/png")},
                headers={"X-Tenant": "sysu"},
            )
            url_b = resp_b.json()["logo_url"]

            assert url_a != url_b
            assert "scnu" in url_a
            assert "sysu" in url_b
