"""Tests for _ensure_tenant_and_admin() in backend/core/startup_seed.py.

Updated to cover the two-account seed contract:
  - admin / admin123  (is_developer=True)
  - scnu  / 2026scnu  (is_developer=False, college admin)
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from core.module_registry import ModuleKey


# 纯单元测试（mock async_session）— 覆盖 conftest.py 的 autouse setup_db，避免连真实 DB
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


# ── Helpers ──

def _scalar_one_or_none_result(value):
    """Mock a query result returning scalar_one_or_none."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = value
    return m


def _route_execute(tenant=None, admin_user=None, admin_link=None,
                   scnu_user=None, scnu_link=None):
    """Return an AsyncMock side_effect that routes by SQL string content.

    Order-independent — matches the real query semantics so tests stay readable
    as the seed function evolves.
    """
    async def _side_effect(stmt, *a, **kw):
        sql = str(stmt)
        if "ALTER TABLE" in sql and "is_developer" in sql:
            return MagicMock()  # DDL result, unused
        if "is_developer" in sql and "users" in sql and "ALTER" not in sql:
            # defensive: shouldn't hit
            return MagicMock()
        if "tenants" in sql.lower() and "slug" in sql.lower():
            return _scalar_one_or_none_result(tenant)
        if "tenant_users" in sql.lower():
            # Distinguish admin vs scnu link by inspecting params is hard;
            # rely on call order via closure counter instead.
            return _scalar_one_or_none_result(admin_link if not _side_effect._scnu_link_phase else scnu_link)
        if "users" in sql.lower() and "username" in sql.lower():
            if not _side_effect._admin_user_phase:
                _side_effect._admin_user_phase = True
                return _scalar_one_or_none_result(admin_user)
            else:
                return _scalar_one_or_none_result(scnu_user)
        return MagicMock()
    _side_effect._admin_user_phase = False
    _side_effect._scnu_link_phase = False
    return _side_effect


def _route_execute_v2(tenant=None, admin_user=None, admin_link=None,
                      scnu_user=None, scnu_link=None):
    """Order-based router using a counter (matches actual call sequence)."""
    state = {"n": 0, "link_calls": 0}
    # Actual call order in _ensure_tenant_and_admin:
    # 0: ALTER TABLE (ddl)
    # 1: select tenant
    # 2: select admin user
    # 3: select admin link
    # 4: select scnu user
    # 5: select scnu link
    async def _side_effect(stmt, *a, **kw):
        n = state["n"]
        state["n"] += 1
        if n == 0:
            return MagicMock()  # ALTER TABLE
        if n == 1:
            return _scalar_one_or_none_result(tenant)
        if n == 2:
            return _scalar_one_or_none_result(admin_user)
        if n == 3:
            return _scalar_one_or_none_result(admin_link)
        if n == 4:
            return _scalar_one_or_none_result(scnu_user)
        if n == 5:
            return _scalar_one_or_none_result(scnu_link)
        return MagicMock()
    return _side_effect


def _make_db_with_routing(**kwargs):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=_route_execute_v2(**kwargs))
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


class TestEnsureTenantAndAdmin:
    """Tests for _ensure_tenant_and_admin()."""

    # ── Normal cases ──

    def test_creates_tenant_when_missing(self):
        """No scnu tenant → creates tenant with brand + modules config."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_user = MagicMock(); existing_user.id = uuid.uuid4(); existing_user.username = "admin"
            existing_link = MagicMock()
            scnu_user = MagicMock(); scnu_user.id = uuid.uuid4()
            scnu_link = MagicMock()

            mock_db = _make_db_with_routing(
                tenant=None, admin_user=existing_user, admin_link=existing_link,
                scnu_user=scnu_user, scnu_link=scnu_link,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            tenant_arg = mock_db.add.call_args_list[0][0][0]
            assert tenant_arg.slug == "scnu"
            assert tenant_arg.name == "华南师范大学"
            assert "modules" in tenant_arg.config
            assert "brand" in tenant_arg.config

    def test_creates_admin_user_when_missing(self):
        """No admin user → creates admin with hashed password and is_developer=True."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock(); existing_tenant.id = uuid.uuid4()
            existing_link = MagicMock()
            scnu_user = MagicMock(); scnu_user.id = uuid.uuid4()
            scnu_link = MagicMock()

            mock_db = _make_db_with_routing(
                tenant=existing_tenant, admin_user=None, admin_link=existing_link,
                scnu_user=scnu_user, scnu_link=scnu_link,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            added = [c[0][0] for c in mock_db.add.call_args_list]
            admin_users = [u for u in added if getattr(u, "username", None) == "admin"]
            assert len(admin_users) == 1
            assert ":" in admin_users[0].password_hash
            assert admin_users[0].is_developer is True

    def test_creates_scnu_user_when_missing(self):
        """No scnu user → creates scnu college admin with is_developer=False."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock(); existing_tenant.id = uuid.uuid4()
            admin_user = MagicMock(); admin_user.id = uuid.uuid4()
            admin_link = MagicMock()
            scnu_link = MagicMock()

            mock_db = _make_db_with_routing(
                tenant=existing_tenant, admin_user=admin_user, admin_link=admin_link,
                scnu_user=None, scnu_link=scnu_link,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            added = [c[0][0] for c in mock_db.add.call_args_list]
            scnu_users = [u for u in added if getattr(u, "username", None) == "scnu"]
            assert len(scnu_users) == 1
            assert scnu_users[0].is_developer is False

    def test_creates_admin_link_when_missing(self):
        """Admin link missing → creates TenantUser role='admin'."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock(); existing_tenant.id = uuid.uuid4()
            admin_user = MagicMock(); admin_user.id = uuid.uuid4()
            scnu_user = MagicMock(); scnu_user.id = uuid.uuid4()
            scnu_link = MagicMock()

            mock_db = _make_db_with_routing(
                tenant=existing_tenant, admin_user=admin_user, admin_link=None,
                scnu_user=scnu_user, scnu_link=scnu_link,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            added = [c[0][0] for c in mock_db.add.call_args_list]
            links = [l for l in added if getattr(l, "role", None) == "admin"]
            assert len(links) == 1  # admin link created
            assert links[0].user_id == admin_user.id

    def test_creates_scnu_link_when_missing(self):
        """Scnu link missing → creates TenantUser role='admin' for scnu user."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock(); existing_tenant.id = uuid.uuid4()
            admin_user = MagicMock(); admin_user.id = uuid.uuid4()
            admin_link = MagicMock()
            scnu_user = MagicMock(); scnu_user.id = uuid.uuid4()

            mock_db = _make_db_with_routing(
                tenant=existing_tenant, admin_user=admin_user, admin_link=admin_link,
                scnu_user=scnu_user, scnu_link=None,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            added = [c[0][0] for c in mock_db.add.call_args_list]
            links = [l for l in added if getattr(l, "role", None) == "admin"]
            assert len(links) == 1  # scnu link created
            assert links[0].user_id == scnu_user.id

    # ── Idempotency ──

    def test_all_exist_no_user_adds(self):
        """Everything exists → no User objects added."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock(); existing_tenant.id = uuid.uuid4()
            admin_user = MagicMock(); admin_user.id = uuid.uuid4(); admin_user.is_developer = False
            admin_link = MagicMock()
            scnu_user = MagicMock(); scnu_user.id = uuid.uuid4(); scnu_user.is_developer = False
            scnu_link = MagicMock()

            mock_db = _make_db_with_routing(
                tenant=existing_tenant, admin_user=admin_user, admin_link=admin_link,
                scnu_user=scnu_user, scnu_link=scnu_link,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            added = [c[0][0] for c in mock_db.add.call_args_list]
            # No User or TenantUser objects added when all exist
            assert not any(getattr(o, "username", None) for o in added)
            assert not any(getattr(o, "role", None) == "admin" for o in added)
            # admin's is_developer flag should still be promoted to True
            assert admin_user.is_developer is True

    def test_promotes_existing_admin_to_developer(self):
        """Existing admin user without is_developer flag → set to True."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock(); existing_tenant.id = uuid.uuid4()
            admin_user = MagicMock(); admin_user.id = uuid.uuid4(); admin_user.is_developer = False
            admin_link = MagicMock()
            scnu_user = MagicMock(); scnu_user.id = uuid.uuid4()
            scnu_link = MagicMock()

            mock_db = _make_db_with_routing(
                tenant=existing_tenant, admin_user=admin_user, admin_link=admin_link,
                scnu_user=scnu_user, scnu_link=scnu_link,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            assert admin_user.is_developer is True
            assert scnu_user.is_developer is False

    # ── Error handling ──

    def test_does_not_crash_on_db_error(self):
        """DB error during queries → logs error, does not raise."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            mock_db = MagicMock()
            mock_db.execute = AsyncMock(side_effect=RuntimeError("DB unavailable"))
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())  # should not raise

    def test_creates_all_when_nothing_exists(self):
        """No tenant/users/links → creates tenant + 2 users + 2 links, commits."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            mock_db = _make_db_with_routing(
                tenant=None, admin_user=None, admin_link=None,
                scnu_user=None, scnu_link=None,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            added = [c[0][0] for c in mock_db.add.call_args_list]
            # tenant + admin user + admin link + scnu user + scnu link = 5
            assert len(added) == 5
            tenants = [o for o in added if getattr(o, "slug", None) == "scnu"]
            assert len(tenants) == 1
            users = [o for o in added if hasattr(o, "password_hash")]
            assert {u.username for u in users} == {"admin", "scnu"}
            admin_u = next(u for u in users if u.username == "admin")
            scnu_u = next(u for u in users if u.username == "scnu")
            assert admin_u.is_developer is True
            assert scnu_u.is_developer is False
            links = [o for o in added if getattr(o, "role", None) == "admin"]
            assert len(links) == 2
            mock_db.commit.assert_called()

    # ── Config validation ──

    def test_tenant_config_includes_all_modules(self):
        """Created tenant config.modules has all ModuleKey entries True."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            admin_user = MagicMock(); admin_user.id = uuid.uuid4()
            admin_link = MagicMock()
            scnu_user = MagicMock(); scnu_user.id = uuid.uuid4()
            scnu_link = MagicMock()

            mock_db = _make_db_with_routing(
                tenant=None, admin_user=admin_user, admin_link=admin_link,
                scnu_user=scnu_user, scnu_link=scnu_link,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            tenant_arg = mock_db.add.call_args_list[0][0][0]
            modules = tenant_arg.config.get("modules", {})
            for key in ModuleKey:
                assert modules.get(key.value) is True, f"Module {key.value} should be enabled"

    def test_tenant_config_includes_brand(self):
        """Created tenant config.brand has required fields."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            admin_user = MagicMock(); admin_user.id = uuid.uuid4()
            admin_link = MagicMock()
            scnu_user = MagicMock(); scnu_user.id = uuid.uuid4()
            scnu_link = MagicMock()

            mock_db = _make_db_with_routing(
                tenant=None, admin_user=admin_user, admin_link=admin_link,
                scnu_user=scnu_user, scnu_link=scnu_link,
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            tenant_arg = mock_db.add.call_args_list[0][0][0]
            brand = tenant_arg.config.get("brand", {})
            assert brand["name"] == "华南师范大学"
            assert "short_name" in brand
            assert "primary_color" in brand
            assert "secondary_color" in brand
