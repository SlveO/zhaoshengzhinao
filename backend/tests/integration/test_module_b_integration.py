"""Integration tests for Module B — contract-driven black-box tests.

Based on docs/contracts/miniapp_sse_contract.md and analytics_consumption_contract.md.
Tests integration between: miniapp chat → profile_bridge → session_profiles → analytics.
Mocks external boundaries (LLM, RAG); uses real DB and real internal modules.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.cend_profile_analyzer import CendExtractionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_llm_streaming(reply_text: str):
    """Create a mock ChatOpenAI whose astream yields chunks with .content."""
    class _MockChunk:
        def __init__(self, text):
            self.content = text

    async def _fake_astream(msgs):
        for token in reply_text.split():
            yield _MockChunk(token + " ")

    mock_llm = MagicMock()
    mock_llm.astream = _fake_astream
    return mock_llm


async def _create_session(async_client, tenant_slug="test"):
    """Create a session via /api/v1/miniapp/enter."""
    resp = await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": tenant_slug, "scene": "test"},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["session_id"]


async def _send_chat_message(async_client, session_id, message, tenant_slug="test"):
    """Send a chat message and collect SSE events."""
    resp = await async_client.post(
        "/api/v1/chat/messages",
        json={
            "session_id": session_id,
            "tenant_slug": tenant_slug,
            "message": {"role": "user", "content": message},
        },
    )
    # Collect SSE events
    events = []
    for line in resp.text.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


# ---------------------------------------------------------------------------
# Integration: miniapp chat → profile_bridge → session_profiles
# ---------------------------------------------------------------------------


class TestChatToProfileBridgeIntegration:
    @pytest.mark.asyncio
    async def test_profile_bridge_triggers_every_3_turns(
        self, async_client, test_tenant, setup_db
    ):
        # Contract: every 3 turns → profile_bridge triggers, profile_updated=True
        # Arrange
        session_id = await _create_session(async_client)
        extraction = CendExtractionResult(
            basic={"province": "广东", "score": 600},
            concerns=["计算机", "人工智能"],
        )
        # Act — send 3 messages, mock LLM + RAG + extraction
        with patch("api.routes.miniapp.ChatOpenAI") as MockLLM, \
             patch("knowledge_base.chroma_client.search_similar", new_callable=AsyncMock) as mock_search, \
             patch("services.profile_bridge.analyze_cend_turn", new_callable=AsyncMock) as mock_analyze:
            MockLLM.return_value = _make_mock_llm_streaming("你好同学，欢迎咨询")
            mock_search.return_value = []
            mock_analyze.return_value = extraction

            # Turn 1 — should NOT trigger bridge (count=1)
            events1 = await _send_chat_message(async_client, session_id, "我是广东考生")
            done1 = next(e for e in events1 if e.get("type") == "done")

            # Turn 2 — should NOT trigger bridge (count=2)
            events2 = await _send_chat_message(async_client, session_id, "我喜欢计算机")
            done2 = next(e for e in events2 if e.get("type") == "done")

            # Turn 3 — SHOULD trigger bridge (count=3)
            events3 = await _send_chat_message(async_client, session_id, "分数600左右")
            done3 = next(e for e in events3 if e.get("type") == "done")

        # Assert — 3rd turn triggers bridge
        assert done3["profile_updated"] is True
        # analyze_cend_turn was called on 3rd turn
        assert mock_analyze.await_count >= 1

    @pytest.mark.asyncio
    async def test_profile_bridge_failure_does_not_block_sse(
        self, async_client, test_tenant, setup_db
    ):
        # Contract: profile_bridge failure → SSE not blocked, only warning
        # Arrange
        session_id = await _create_session(async_client)
        with patch("api.routes.miniapp.ChatOpenAI") as MockLLM, \
             patch("knowledge_base.chroma_client.search_similar", new_callable=AsyncMock) as mock_search, \
             patch("services.profile_bridge.analyze_cend_turn", new_callable=AsyncMock) as mock_analyze:
            MockLLM.return_value = _make_mock_llm_streaming("你好")
            mock_search.return_value = []
            mock_analyze.side_effect = Exception("LLM extraction failed")

            # Send 3 messages to trigger bridge
            for i in range(3):
                events = await _send_chat_message(async_client, session_id, f"消息{i}")

        # Assert — last response has done event (not blocked by bridge failure)
        done = next(e for e in events if e.get("type") == "done")
        assert done is not None
        assert "assistant_message" in done

    @pytest.mark.asyncio
    async def test_session_profiles_written_after_bridge(
        self, async_client, test_tenant, setup_db
    ):
        # Contract: bridge success → writes session_profiles table
        # Arrange
        session_id = await _create_session(async_client)
        extraction = CendExtractionResult(
            basic={"province": "广东", "score": 600},
            concerns=["计算机"],
        )
        with patch("api.routes.miniapp.ChatOpenAI") as MockLLM, \
             patch("knowledge_base.chroma_client.search_similar", new_callable=AsyncMock) as mock_search, \
             patch("services.profile_bridge.analyze_cend_turn", new_callable=AsyncMock) as mock_analyze:
            MockLLM.return_value = _make_mock_llm_streaming("你好同学")
            mock_search.return_value = []
            mock_analyze.return_value = extraction

            # Send 3 messages
            for i in range(3):
                await _send_chat_message(async_client, session_id, f"消息{i}")

        # Assert — verify session_profiles table has data
        from models import async_session
        from tenants.models import SessionProfile
        from sqlalchemy import select
        async with async_session() as db:
            stmt = select(SessionProfile).where(SessionProfile.tenant_id == test_tenant.id)
            result = await db.execute(stmt)
            profiles = result.scalars().all()
            assert len(profiles) >= 1
            assert profiles[0].profile_json["basic"]["province"] == "广东"


# ---------------------------------------------------------------------------
# Integration: session_profiles → analytics topic_cloud
# ---------------------------------------------------------------------------


class TestProfileToAnalyticsIntegration:
    @pytest.mark.asyncio
    async def test_topic_cloud_consumes_concerns_from_profiles(
        self, setup_db, test_tenant, seed_session_profile, seed_event
    ):
        # Contract: topic_cloud consumes session_profiles.concerns (weight x2)
        # Arrange — seed profile with concerns
        await seed_session_profile(
            tenant_id=test_tenant.id,
            profile_json={"concerns": ["计算机科学", "人工智能"]},
        )
        # Seed a chat message event with same word to verify x2 boost
        await seed_event(
            "chat.message_sent",
            tenant_id=test_tenant.id,
            payload={"content": "计算机科学专业怎么样"},
        )
        # Act
        from analytics.topic_cloud import get_topic_cloud
        result = await get_topic_cloud(str(test_tenant.id), days=30)
        # Assert — concerns appear with boosted count
        words = {item["word"]: item["count"] for item in result}
        # 计算机科学 should appear (from both concerns x2 and chat x1 = 3, or just concerns x2)
        assert "计算机科学" in words
        assert words["计算机科学"] >= 2

    @pytest.mark.asyncio
    async def test_full_pipeline_chat_to_analytics(
        self, async_client, test_tenant, setup_db
    ):
        # Full pipeline: chat → bridge → session_profiles → topic_cloud
        # Arrange
        session_id = await _create_session(async_client)
        extraction = CendExtractionResult(
            basic={"province": "广东"},
            concerns=["集成测试词"],
        )
        with patch("api.routes.miniapp.ChatOpenAI") as MockLLM, \
             patch("knowledge_base.chroma_client.search_similar", new_callable=AsyncMock) as mock_search, \
             patch("services.profile_bridge.analyze_cend_turn", new_callable=AsyncMock) as mock_analyze:
            MockLLM.return_value = _make_mock_llm_streaming("你好")
            mock_search.return_value = []
            mock_analyze.return_value = extraction

            # Send 3 messages to trigger bridge
            for i in range(3):
                await _send_chat_message(async_client, session_id, f"消息{i}")

        # Act — query topic_cloud
        from analytics.topic_cloud import get_topic_cloud
        result = await get_topic_cloud(str(test_tenant.id), days=30)
        words = [item["word"] for item in result]
        # Assert — the concern from bridge extraction appears in topic_cloud
        assert "集成测试词" in words


# ---------------------------------------------------------------------------
# Integration: tenant isolation across pipeline
# ---------------------------------------------------------------------------


class TestTenantIsolationIntegration:
    @pytest.mark.asyncio
    async def test_profile_tenant_isolation(
        self, setup_db, test_tenant, other_tenant, seed_session_profile
    ):
        # Contract: tenant isolation — A tenant's profiles not visible to B
        # Arrange
        await seed_session_profile(
            tenant_id=test_tenant.id,
            profile_json={"concerns": ["租户A专属词"]},
        )
        await seed_session_profile(
            tenant_id=other_tenant.id,
            profile_json={"concerns": ["租户B专属词"]},
        )
        # Act
        from analytics.topic_cloud import get_topic_cloud
        result_a = await get_topic_cloud(str(test_tenant.id), days=30)
        result_b = await get_topic_cloud(str(other_tenant.id), days=30)
        words_a = [item["word"] for item in result_a]
        words_b = [item["word"] for item in result_b]
        # Assert
        assert "租户A专属词" in words_a
        assert "租户A专属词" not in words_b
        assert "租户B专属词" in words_b
        assert "租户B专属词" not in words_a
