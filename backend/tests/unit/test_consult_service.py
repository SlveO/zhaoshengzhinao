"""Pipeline stage: Student Entry — session create/resume, profile update, chat history."""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from services.consult_service import (
    get_or_create_session,
    get_session,
    update_session_profile,
    get_chat_history,
    save_message,
    build_profile_summary,
)


class TestGetOrCreateSession:
    """Pipeline stage: Student Entry — session creation and resumption."""

    @pytest.mark.asyncio
    async def test_create_new_session_when_session_id_is_none(self):
        """Creating with session_id=None generates a new sess_xxx session."""
        mock_session_obj = MagicMock()
        mock_session_obj.session_id = "sess_new123"
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            session, is_new = await get_or_create_session(None, "scnu")

            assert is_new is True
            assert session.session_id.startswith("sess_")

    @pytest.mark.asyncio
    async def test_resume_existing_session_by_id(self):
        """Providing an existing session_id returns the same session, is_new=False."""
        existing = MagicMock()
        existing.session_id = "sess_abc123"
        existing.expires_at = None  # never expires
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
        )
        mock_db.commit = AsyncMock()

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            session, is_new = await get_or_create_session("sess_abc123", "scnu")

            assert is_new is False
            assert session.session_id == "sess_abc123"

    @pytest.mark.asyncio
    async def test_create_session_with_preset_id_when_not_found(self):
        """If session_id is provided but not found in DB, create a fresh session_id to avoid UNIQUE conflicts."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            session, is_new = await get_or_create_session("old_nonexistent_id", "scnu")

            assert is_new is True
            # Provided ID is reused when not found in DB
            assert session.session_id == "old_nonexistent_id"


class TestGetSession:
    """Pipeline stage: Student Entry — single session retrieval."""

    @pytest.mark.asyncio
    async def test_get_session_returns_session_when_found(self):
        existing = MagicMock()
        existing.session_id = "sess_found"
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
        )

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            result = await get_session("sess_found")
            assert result is not None
            assert result.session_id == "sess_found"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_when_not_found(self):
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            result = await get_session("sess_missing")
            assert result is None


class TestUpdateSessionProfile:
    """Pipeline stage: Student Entry — profile field updates on ConsultSession."""

    @pytest.mark.asyncio
    async def test_update_profile_sets_province_and_score(self):
        session_mock = MagicMock()
        session_mock.province = ""
        session_mock.score = 0
        session_mock.subject_type = ""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=session_mock))
        )
        mock_db.commit = AsyncMock()

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await update_session_profile("sess_x", {"province": "广东", "score": 600})

            assert session_mock.province == "广东"
            assert session_mock.score == 600

    @pytest.mark.asyncio
    async def test_update_profile_skips_empty_values(self):
        session_mock = MagicMock()
        session_mock.province = "广东"
        session_mock.score = 600
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=session_mock))
        )
        mock_db.commit = AsyncMock()

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await update_session_profile("sess_x", {"province": "", "score": 0})

            assert session_mock.province == "广东"
            assert session_mock.score == 600

    @pytest.mark.asyncio
    async def test_update_profile_noop_when_session_not_found(self):
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_db.commit = AsyncMock()

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            # Should not raise
            await update_session_profile("sess_missing", {"province": "广东"})


class TestChatHistoryAndMessages:
    """Pipeline stage: AI Conversation — message persistence and retrieval."""

    @pytest.mark.asyncio
    async def test_save_message_returns_message_dict(self):
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        async def _fake_refresh(obj):
            obj.created_at = MagicMock(isoformat=MagicMock(return_value="2026-05-29T00:00:00"))
        mock_db.refresh = AsyncMock(side_effect=_fake_refresh)
        mock_db.add = MagicMock()

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            result = await save_message("sess_x", "user", "Hello")
            assert result["role"] == "user"
            assert result["content"] == "Hello"
            assert "message_id" in result

    @pytest.mark.asyncio
    async def test_get_chat_history_returns_messages_ordered(self):
        msg1 = MagicMock()
        msg1.id = "id-1"
        msg1.role = "user"
        msg1.content = "Hi"
        msg1.created_at = MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:00"))

        msg2 = MagicMock()
        msg2.id = "id-2"
        msg2.role = "assistant"
        msg2.content = "Hello"
        msg2.created_at = MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:01"))

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [msg1, msg2]
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=mock_scalars))
        )

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            history = await get_chat_history("sess_x")
            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"


class TestBuildProfileSummary:
    """Pipeline stage: Profile Extraction — summary construction from session."""

    def test_build_profile_summary_returns_none_when_empty(self):
        session = MagicMock()
        session.province = ""
        session.subject_type = ""
        session.score = 0
        session.intent_majors = []
        session.focus_points = []

        result = build_profile_summary(session)
        assert result is None

    def test_build_profile_summary_returns_dict_with_data(self):
        session = MagicMock()
        session.province = "广东"
        session.subject_type = "物理类"
        session.score = 620
        session.intent_majors = ["计算机"]
        session.focus_points = ["就业"]

        result = build_profile_summary(session)
        assert result is not None
        assert result["province"] == "广东"
        assert result["score"] == 620
        assert result["intent_majors"] == ["计算机"]


class TestGuestVsRegistered:
    """Pipeline stage: Student Entry — guest vs registered user distinction."""

    @pytest.mark.asyncio
    async def test_new_session_has_no_user_id_for_guest(self):
        """Guest sessions are created without a user_id (None)."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            session, is_new = await get_or_create_session(None, "scnu")
            assert is_new is True

    @pytest.mark.asyncio
    async def test_tenant_slug_is_set_on_creation(self):
        """New sessions are tagged with the correct tenant_slug."""
        captured_slug = []

        def capture_add(session):
            captured_slug.append(session.tenant_slug)

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock(side_effect=capture_add)

        with patch("services.consult_service.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await get_or_create_session(None, "scnu")
            assert "scnu" in captured_slug


class TestSessionTTL:

    @pytest.mark.asyncio
    async def test_create_registered_session_30day_ttl(self):
        captured: dict = {}
        class FakeSession:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            with patch("services.consult_service.ConsultSession", FakeSession):
                session, is_new = await get_or_create_session(
                    None, "scnu", user_id=uuid.UUID("11111111-1111-1111-1111-111111111111")
                )
                assert is_new is True
                assert captured["user_id"] == uuid.UUID("11111111-1111-1111-1111-111111111111")
                now = datetime.now(timezone.utc)
                ttl = captured["expires_at"] - now
                assert timedelta(days=29) < ttl < timedelta(days=31)

    @pytest.mark.asyncio
    async def test_create_guest_session_1day_ttl(self):
        captured: dict = {}
        class FakeSession:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            with patch("services.consult_service.ConsultSession", FakeSession):
                session, is_new = await get_or_create_session(None, "scnu")
                assert is_new is True
                assert captured["user_id"] is None
                now = datetime.now(timezone.utc)
                ttl = captured["expires_at"] - now
                assert timedelta(hours=23) < ttl < timedelta(hours=25)

    @pytest.mark.asyncio
    async def test_resume_valid_session_unchanged_ttl(self):
        now = datetime.now(timezone.utc)
        existing = MagicMock()
        existing.session_id = "sess_abc"
        existing.expires_at = now + timedelta(hours=12)
        existing.tenant_slug = "scnu"

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            session, is_new = await get_or_create_session("sess_abc", "scnu")
            assert is_new is False
            assert session.session_id == "sess_abc"
            assert session.expires_at == existing.expires_at

    @pytest.mark.asyncio
    async def test_expired_guest_session_triggers_new(self):
        now = datetime.now(timezone.utc)
        old = MagicMock()
        old.session_id = "sess_old_guest"
        old.expires_at = now - timedelta(hours=1)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mr = MagicMock()
        mr.scalar_one_or_none.return_value = old
        mock_db.execute = AsyncMock(return_value=mr)

        captured_session = None

        def capture_add(session):
            nonlocal captured_session
            captured_session = session

        mock_db.add = MagicMock(side_effect=capture_add)
        mock_db.refresh = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.delete = AsyncMock()

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            session, is_new = await get_or_create_session("sess_old_guest", "scnu")
            assert is_new is True
            assert captured_session is not None
            assert captured_session.session_id == "sess_old_guest"

    @pytest.mark.asyncio
    async def test_expired_session_does_not_reuse_session_id(self):
        now = datetime.now(timezone.utc)
        old = MagicMock()
        old.session_id = "sess_will_expire"
        old.expires_at = now - timedelta(days=2)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mr = MagicMock()
        mr.scalar_one_or_none.return_value = old
        mock_db.execute = AsyncMock(return_value=mr)

        captured_session = None

        def capture_add(session):
            nonlocal captured_session
            captured_session = session

        mock_db.add = MagicMock(side_effect=capture_add)
        mock_db.refresh = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.delete = AsyncMock()

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            session, is_new = await get_or_create_session("sess_will_expire", "scnu")
            assert captured_session.session_id == "sess_will_expire"

    @pytest.mark.asyncio
    async def test_resume_does_not_extend_ttl(self):
        now = datetime.now(timezone.utc)
        orig = now + timedelta(hours=5)
        existing = MagicMock()
        existing.session_id = "sess_no_extend"
        existing.expires_at = orig

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mr = MagicMock()
        mr.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mr)

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            session, is_new = await get_or_create_session("sess_no_extend", "scnu")
            assert is_new is False
            assert session.expires_at == orig
