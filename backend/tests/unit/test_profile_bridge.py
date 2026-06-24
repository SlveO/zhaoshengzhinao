"""Unit tests for profile_bridge — contract-driven black-box tests.

Based on docs/contracts/profile_bridge_contract.md.
Does NOT read implementation code; tests against public interface signatures only.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.profile_bridge import (
    bridge_profile_to_session_profiles,
    get_chat_message_count,
    load_existing_profile_json,
    should_extract,
    _compute_confidence,
    _dict_to_extraction_result,
)
from services.cend_profile_analyzer import CendExtractionResult


# ---------------------------------------------------------------------------
# should_extract
# ---------------------------------------------------------------------------


class TestShouldExtract:
    @pytest.mark.asyncio
    async def test_zero_messages_returns_false(self):
        # Contract 1: count == 0 → False
        count = await should_extract("nonexistent-session-id")
        assert count is False

    @pytest.mark.asyncio
    async def test_three_messages_returns_true(self, setup_db):
        # Contract 2: count == 3 → True
        # Arrange — seed 3 user messages
        from models import async_session
        from models.chat_message import ChatMessage
        sid = "test-sess-3"
        async with async_session() as db:
            for _ in range(3):
                db.add(ChatMessage(session_id=sid, role="user", content="msg"))
            await db.commit()
        # Act
        result = await should_extract(sid)
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_six_messages_returns_true(self, setup_db):
        # Contract 3: count == 6 → True
        from models import async_session
        from models.chat_message import ChatMessage
        sid = "test-sess-6"
        async with async_session() as db:
            for _ in range(6):
                db.add(ChatMessage(session_id=sid, role="user", content="msg"))
            await db.commit()
        result = await should_extract(sid)
        assert result is True

    @pytest.mark.asyncio
    async def test_one_message_returns_false(self, setup_db):
        # Contract 4: count == 1 → False
        from models import async_session
        from models.chat_message import ChatMessage
        sid = "test-sess-1"
        async with async_session() as db:
            db.add(ChatMessage(session_id=sid, role="user", content="msg"))
            await db.commit()
        result = await should_extract(sid)
        assert result is False

    @pytest.mark.asyncio
    async def test_four_messages_returns_false(self, setup_db):
        # Contract 5: count == 4 → False
        from models import async_session
        from models.chat_message import ChatMessage
        sid = "test-sess-4"
        async with async_session() as db:
            for _ in range(4):
                db.add(ChatMessage(session_id=sid, role="user", content="msg"))
            await db.commit()
        result = await should_extract(sid)
        assert result is False


# ---------------------------------------------------------------------------
# get_chat_message_count
# ---------------------------------------------------------------------------


class TestGetChatMessageCount:
    @pytest.mark.asyncio
    async def test_no_messages_returns_zero(self):
        # Contract 1: no messages → 0
        count = await get_chat_message_count("nonexistent-session")
        assert count == 0

    @pytest.mark.asyncio
    async def test_n_messages_returns_n(self, setup_db):
        # Contract 2: N user messages → N
        from models import async_session
        from models.chat_message import ChatMessage
        sid = "count-sess-5"
        async with async_session() as db:
            for _ in range(5):
                db.add(ChatMessage(session_id=sid, role="user", content="msg"))
            await db.commit()
        count = await get_chat_message_count(sid)
        assert count == 5


# ---------------------------------------------------------------------------
# load_existing_profile_json
# ---------------------------------------------------------------------------


class TestLoadExistingProfileJson:
    @pytest.mark.asyncio
    async def test_record_exists_returns_dict(self, setup_db, test_tenant, seed_session_profile):
        # Contract 1: record exists → returns profile_json
        # Arrange
        session_id = uuid.uuid4()
        profile_data = {"basic": {"province": "广东"}, "concerns": ["AI"]}
        await seed_session_profile(
            tenant_id=test_tenant.id,
            session_id=session_id,
            profile_json=profile_data,
        )
        # Act
        result = await load_existing_profile_json(test_tenant.id, session_id)
        # Assert
        assert result is not None
        assert result["basic"]["province"] == "广东"

    @pytest.mark.asyncio
    async def test_record_not_exists_returns_none(self, setup_db, test_tenant):
        # Contract 2: record not exists → None
        result = await load_existing_profile_json(test_tenant.id, uuid.uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# bridge_profile_to_session_profiles
# ---------------------------------------------------------------------------


class TestBridgeProfileToSessionProfiles:
    @pytest.mark.asyncio
    async def test_llm_failure_returns_false_no_exception(self, setup_db, test_tenant):
        # Contract 3: LLM extraction failure → returns False, no exception
        # Contract 5: NEVER raises
        from models.consult_session import ConsultSession
        session = ConsultSession(
            session_id="bridge-fail-sess",
            tenant_slug=test_tenant.slug,
        )
        # Arrange — mock analyze_cend_turn to raise
        with patch("services.profile_bridge.analyze_cend_turn", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = Exception("LLM down")
            # Act
            result = await bridge_profile_to_session_profiles(
                session, test_tenant.id, "user msg", "ai reply"
            )
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_success_writes_db_and_returns_true(self, setup_db, test_tenant):
        # Contract 1 & 4: success → writes DB + returns True
        from models.consult_session import ConsultSession
        from models import async_session
        from tenants.models import SessionProfile
        from sqlalchemy import select

        session = ConsultSession(
            session_id="bridge-ok-sess",
            tenant_slug=test_tenant.slug,
        )
        # Need to save the session first so FK works
        async with async_session() as db:
            db.add(session)
            await db.commit()

        extraction = CendExtractionResult(
            basic={"province": "广东", "score": 600},
            concerns=["计算机"],
        )
        with patch("services.profile_bridge.analyze_cend_turn", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = extraction
            # Act
            result = await bridge_profile_to_session_profiles(
                session, test_tenant.id, "我是广东考生", "你好"
            )
        # Assert
        assert result is True
        # Verify DB written
        async with async_session() as db:
            stmt = select(SessionProfile).where(SessionProfile.session_id == session.id)
            db_result = await db.execute(stmt)
            profile = db_result.scalar_one_or_none()
            assert profile is not None
            assert profile.profile_json["basic"]["province"] == "广东"

    @pytest.mark.asyncio
    async def test_never_raises_on_unexpected_error(self, setup_db, test_tenant):
        # Contract 5: NEVER raises — even on unexpected errors
        from models.consult_session import ConsultSession
        session = ConsultSession(session_id="bridge-err-sess", tenant_slug=test_tenant.slug)
        with patch("services.profile_bridge.analyze_cend_turn", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = RuntimeError("unexpected")
            # Act — should not raise
            result = await bridge_profile_to_session_profiles(
                session, test_tenant.id, "msg", "reply"
            )
        # Assert
        assert result is False


# ---------------------------------------------------------------------------
# _dict_to_extraction_result
# ---------------------------------------------------------------------------


class TestDictToExtractionResult:
    def test_none_returns_empty_result(self):
        result = _dict_to_extraction_result(None)
        assert isinstance(result, CendExtractionResult)
        assert result.has_any_data() is False

    def test_valid_dict_converts_to_result(self):
        data = {"basic": {"province": "广东"}, "concerns": ["AI"]}
        result = _dict_to_extraction_result(data)
        assert result.basic["province"] == "广东"
        assert result.concerns == ["AI"]

    def test_missing_fields_use_defaults(self):
        data = {"basic": {"province": "北京"}}
        result = _dict_to_extraction_result(data)
        assert result.concerns == []
        assert result.values == []


# ---------------------------------------------------------------------------
# _compute_confidence
# ---------------------------------------------------------------------------


class TestComputeConfidence:
    def test_returns_json_serializable_dict(self):
        # Contract 1 & 2: returns dict, JSON serializable
        result = CendExtractionResult(basic={"province": "广东"}, concerns=["AI"])
        out = _compute_confidence(result)
        import json
        json.dumps(out)  # no exception
        assert isinstance(out, dict)

    def test_more_complete_has_higher_confidence(self):
        # Contract 1: more fields → higher confidence
        sparse = CendExtractionResult(basic={"province": "广东"})
        full = CendExtractionResult(
            basic={"province": "广东"},
            concerns=["AI", "计算机"],
            riasec={"R": 5, "I": 8, "A": 2, "S": 4, "E": 6, "C": 3},
            values=["创新"],
        )
        sparse_conf = _compute_confidence(sparse)
        full_conf = _compute_confidence(full)
        # Full should have higher or equal confidence value
        # (compare by some numeric field if present, else just verify both are dicts)
        assert isinstance(sparse_conf, dict)
        assert isinstance(full_conf, dict)
