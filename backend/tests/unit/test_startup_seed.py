import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from core.module_registry import ModuleKey


# ── Helpers ──

def _make_db_mock(execute_return=None, execute_side_effect=None):
    """Create a mock async DB session."""
    db = MagicMock()
    db.execute = AsyncMock(return_value=execute_return, side_effect=execute_side_effect)
    return db


def _scalar_result(value):
    """Mock a query result returning a single scalar."""
    m = MagicMock()
    m.scalar.return_value = value
    return m


def _scalar_one_or_none_result(value):
    """Mock a query result returning scalar_one_or_none."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = value
    return m


class TestEnsureTenantAndAdmin:
    """Tests for _ensure_tenant_and_admin() in backend/core/startup_seed.py."""

    # ── Normal cases ──

    def test_creates_tenant_when_missing(self):
        """No scnu tenant in DB → creates tenant with brand + modules config."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            # 1st query: tenant check → None (missing)
            # 2nd query: user check → return existing user (skip user creation)
            # 3rd query: tenant_user check → return existing link (skip link)
            no_tenant = _scalar_one_or_none_result(None)
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            existing_user.username = "admin"
            existing_link = MagicMock()
            existing_link.id = uuid.uuid4()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    no_tenant,
                    _scalar_one_or_none_result(existing_user),
                    _scalar_one_or_none_result(existing_link),
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            # Verify tenant was created
            add_calls = mock_db.add.call_args_list
            assert len(add_calls) >= 1
            # First add should be a Tenant
            tenant_arg = add_calls[0][0][0]
            assert tenant_arg.slug == "scnu"
            assert tenant_arg.name == "华南师范大学"
            assert tenant_arg.status == "active"
            assert "modules" in tenant_arg.config
            assert "brand" in tenant_arg.config

    def test_creates_user_when_missing(self):
        """No admin user → creates user with hashed password."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock()
            existing_tenant.id = uuid.uuid4()
            existing_tenant.slug = "scnu"
            no_user = _scalar_one_or_none_result(None)
            existing_link = MagicMock()
            existing_link.id = uuid.uuid4()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    _scalar_one_or_none_result(existing_tenant),
                    no_user,
                    _scalar_one_or_none_result(existing_link),
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            add_calls = mock_db.add.call_args_list
            assert len(add_calls) >= 1
            user_arg = add_calls[0][0][0]
            assert user_arg.username == "admin"
            assert ":" in user_arg.password_hash  # salt:hash format

    def test_creates_tenant_user_link_when_missing(self):
        """Tenant and user exist but no link → creates TenantUser with role='admin'."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock()
            existing_tenant.id = uuid.uuid4()
            existing_tenant.slug = "scnu"
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            existing_user.username = "admin"
            no_link = _scalar_one_or_none_result(None)

            mock_db = _make_db_mock(
                execute_side_effect=[
                    _scalar_one_or_none_result(existing_tenant),
                    _scalar_one_or_none_result(existing_user),
                    no_link,
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            add_calls = mock_db.add.call_args_list
            assert len(add_calls) >= 1
            link_arg = add_calls[0][0][0]
            assert link_arg.role == "admin"

    # ── Idempotency ──

    def test_skips_tenant_when_exists(self):
        """scnu tenant already exists → no tenant creation."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock()
            existing_tenant.id = uuid.uuid4()
            existing_tenant.slug = "scnu"
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            existing_link = MagicMock()
            existing_link.id = uuid.uuid4()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    _scalar_one_or_none_result(existing_tenant),
                    _scalar_one_or_none_result(existing_user),
                    _scalar_one_or_none_result(existing_link),
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            # No add() calls since everything exists
            mock_db.add.assert_not_called()
            # commit should still be called (to finalize)
            # but add should NOT be called

    def test_skips_user_when_exists(self):
        """admin user already exists → no user creation."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock()
            existing_tenant.id = uuid.uuid4()
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            existing_link = MagicMock()
            existing_link.id = uuid.uuid4()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    _scalar_one_or_none_result(existing_tenant),
                    _scalar_one_or_none_result(existing_user),
                    _scalar_one_or_none_result(existing_link),
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            # No user should be added
            for add_call in mock_db.add.call_args_list:
                arg = add_call[0][0]
                assert not hasattr(arg, "username") or arg.username != "admin"

    def test_skips_link_when_exists(self):
        """tenant_user link already exists → no link creation."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock()
            existing_tenant.id = uuid.uuid4()
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            existing_link = MagicMock()
            existing_link.id = uuid.uuid4()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    _scalar_one_or_none_result(existing_tenant),
                    _scalar_one_or_none_result(existing_user),
                    _scalar_one_or_none_result(existing_link),
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            # No TenantUser should be added
            for add_call in mock_db.add.call_args_list:
                arg = add_call[0][0]
                assert not hasattr(arg, "role") or arg.role != "admin"

    # ── Edge cases ──

    def test_creates_user_when_tenant_exists_but_user_missing(self):
        """Tenant exists, user missing → creates user and link."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock()
            existing_tenant.id = uuid.uuid4()
            no_user = _scalar_one_or_none_result(None)
            existing_link = MagicMock()
            existing_link.id = uuid.uuid4()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    _scalar_one_or_none_result(existing_tenant),
                    no_user,
                    _scalar_one_or_none_result(existing_link),
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            add_calls = mock_db.add.call_args_list
            # Should have added user (and possibly link)
            users_added = [
                c for c in add_calls
                if hasattr(c[0][0], "username") and c[0][0].username == "admin"
            ]
            assert len(users_added) == 1

    def test_creates_link_when_both_exist_but_link_missing(self):
        """Tenant and user exist, link missing → creates only the link."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock()
            existing_tenant.id = uuid.uuid4()
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            no_link = _scalar_one_or_none_result(None)

            mock_db = _make_db_mock(
                execute_side_effect=[
                    _scalar_one_or_none_result(existing_tenant),
                    _scalar_one_or_none_result(existing_user),
                    no_link,
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            add_calls = mock_db.add.call_args_list
            # Should have added a link but no tenant or user
            links_added = [
                c for c in add_calls
                if hasattr(c[0][0], "role") and c[0][0].role == "admin"
            ]
            assert len(links_added) == 1

    def test_all_exist_no_writes(self):
        """Everything exists → zero add() calls."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            existing_tenant = MagicMock()
            existing_tenant.id = uuid.uuid4()
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            existing_link = MagicMock()
            existing_link.id = uuid.uuid4()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    _scalar_one_or_none_result(existing_tenant),
                    _scalar_one_or_none_result(existing_user),
                    _scalar_one_or_none_result(existing_link),
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            assert mock_db.add.call_count == 0

    # ── Error handling ──

    def test_creates_all_when_nothing_exists(self):
        """No tenant, user, or link → creates all three and commits."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            no_tenant = _scalar_one_or_none_result(None)
            no_user = _scalar_one_or_none_result(None)
            no_link = _scalar_one_or_none_result(None)

            mock_db = _make_db_mock(
                execute_side_effect=[no_tenant, no_user, no_link]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            add_calls = mock_db.add.call_args_list
            assert len(add_calls) == 3
            # First: Tenant
            assert add_calls[0][0][0].slug == "scnu"
            # Second: User
            assert add_calls[1][0][0].username == "admin"
            # Third: TenantUser link
            assert add_calls[2][0][0].role == "admin"
            mock_db.commit.assert_called()

    def test_does_not_crash_on_db_error(self):
        """DB error during queries → logs error, does not raise."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            mock_db = MagicMock()
            mock_db.execute = AsyncMock(side_effect=RuntimeError("DB unavailable"))
            mock_session.return_value.__aenter__.return_value = mock_db

            # Should not raise
            asyncio.run(_ensure_tenant_and_admin())

    # ── Config validation ──

    def test_tenant_config_includes_all_modules(self):
        """Created tenant config.modules has all ModuleKey entries set to True."""
        from core.startup_seed import _ensure_tenant_and_admin
        import asyncio

        with patch("models.async_session") as mock_session:
            no_tenant = _scalar_one_or_none_result(None)
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            existing_link = MagicMock()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    no_tenant,
                    _scalar_one_or_none_result(existing_user),
                    _scalar_one_or_none_result(existing_link),
                ]
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
            no_tenant = _scalar_one_or_none_result(None)
            existing_user = MagicMock()
            existing_user.id = uuid.uuid4()
            existing_link = MagicMock()

            mock_db = _make_db_mock(
                execute_side_effect=[
                    no_tenant,
                    _scalar_one_or_none_result(existing_user),
                    _scalar_one_or_none_result(existing_link),
                ]
            )
            mock_session.return_value.__aenter__.return_value = mock_db

            asyncio.run(_ensure_tenant_and_admin())

            tenant_arg = mock_db.add.call_args_list[0][0][0]
            brand = tenant_arg.config.get("brand", {})
            assert "name" in brand
            assert "short_name" in brand
            assert "primary_color" in brand
            assert "secondary_color" in brand
            assert brand["name"] == "华南师范大学"
