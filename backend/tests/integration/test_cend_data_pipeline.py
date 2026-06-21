"""Integration tests for C-end data pipeline — SSE chat + profile bridge + tenant isolation.

Tests:
  1. SSE chat triggers bridge on 3rd user message
  2. SessionProfile row has correct profile_json after extraction
  3. JSON backup file written after extraction
  4. Tenant isolation: Tenant A cannot read Tenant B's session_profiles

All tests mock external LLM calls. DB is real (test PostgreSQL via conftest).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from models import async_session
from models.consult_session import ConsultSession
from tenants.models import SessionProfile
from services.cend_profile_analyzer import CendExtractionResult
from services.profile_bridge import (
    bridge_profile_to_session_profiles,
    load_existing_profile_json,
    get_chat_message_count,
)
from services.consult_service import get_session, save_message
from sqlalchemy import select

from conftest import TEST_TENANT_ID, OTHER_TENANT_ID


# ---------------------------------------------------------------------------
# Mock helpers — shared across tests
# ---------------------------------------------------------------------------


class _FakeChunk:
    """Fake LangChain chat chunk with a .content attribute."""

    def __init__(self, content: str):
        self.content = content


async def _fake_token_stream():
    """Async generator yielding fake LLM tokens for SSE streaming."""
    yield _FakeChunk("token1")
    yield _FakeChunk("token2")
    yield _FakeChunk("token3")


async def _fake_analyze_cend_success(user_msg, ai_reply, existing_profile=None, conversation_history=None):
    """Return a realistic CendExtractionResult with known data."""
    result = CendExtractionResult()
    result.basic["province"] = "Guangdong"
    result.basic["subject_type"] = "Physics"
    result.basic["score"] = 610
    result.interests["preferred_subjects"] = ["Math", "Physics"]
    result.interests["strong_subjects"] = ["Math"]
    result.values = ["CS", "AI"]
    result.riasec["I"] = 7
    result.riasec["R"] = 5
    result.riasec["S"] = 3
    result.region_pref["province"] = "Guangdong"
    result.region_pref["city"] = "Guangzhou"
    result.concerns = ["employment"]
    result.completeness = "L2"
    return result


# ---------------------------------------------------------------------------
# Helper: create a session with N seeded user messages
# ---------------------------------------------------------------------------


async def _create_session_with_messages(async_client, test_tenant, num_user_messages: int):
    """Create a new mini-app session and seed N user messages. Returns (session_orm, session_id_str)."""
    resp = await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": "test"},
    )
    assert resp.status_code == 200
    session_id_str = resp.json()["data"]["session_id"]

    session_orm = await get_session(session_id_str)
    assert session_orm is not None

    for i in range(num_user_messages):
        await save_message(session_id_str, "user", f"test message {i + 1}")

    return session_orm, session_id_str


# ===================================================================
# Test 1: SSE triggers bridge on 3rd user message
# ===================================================================


@pytest.mark.asyncio
async def test_sse_chat_triggers_bridge_on_3rd_message(async_client, test_tenant):
    """Send 3rd user message via SSE; verify session_profiles has data after bridge fires."""
    # --- Arrange ---
    session_orm, session_id_str = await _create_session_with_messages(
        async_client, test_tenant, 2
    )
    session_uuid = session_orm.id

    # Verify no SessionProfile exists yet
    async with async_session() as db:
        result = await db.execute(
            select(SessionProfile).where(
                SessionProfile.tenant_id == TEST_TENANT_ID,
                SessionProfile.session_id == session_uuid,
            )
        )
        assert result.scalar_one_or_none() is None

    # Mock ChatOpenAI for SSE streaming
    mock_llm = MagicMock()
    mock_llm.astream = MagicMock(return_value=_fake_token_stream())

    with patch("langchain_openai.ChatOpenAI", return_value=mock_llm):
        with patch(
            "services.profile_bridge.analyze_cend_turn",
            side_effect=_fake_analyze_cend_success,
        ):
            # --- Act ---
            async with async_client.stream(
                "POST",
                "/api/v1/chat/messages",
                json={
                    "session_id": session_id_str,
                    "tenant_slug": "test",
                    "message": {"role": "user", "content": "my score is 610 from Guangdong physics"},
                },
            ) as response:
                assert response.status_code == 200
                done_seen = False
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        event_data = json.loads(line[6:])
                        if event_data.get("type") == "done":
                            done_seen = True
                assert done_seen, "SSE stream should emit a done event"

    # --- Assert ---
    async with async_session() as db:
        result = await db.execute(
            select(SessionProfile).where(
                SessionProfile.tenant_id == TEST_TENANT_ID,
                SessionProfile.session_id == session_uuid,
            )
        )
        profile = result.scalar_one_or_none()
        assert profile is not None, "SessionProfile must exist after 3rd message"
        assert isinstance(profile.profile_json, dict)
        assert profile.profile_json.get("basic", {}).get("province") == "Guangdong"
        assert profile.profile_json.get("basic", {}).get("score") == 610
        assert profile.completeness == "L2"


# ===================================================================
# Test 2: SessionProfile has correct profile_json fields after extraction
# ===================================================================


@pytest.mark.asyncio
async def test_session_profiles_has_profile_json_after_extraction(
    async_client, test_tenant
):
    """After bridge runs, SessionProfile row exists with all expected profile_json fields."""
    # --- Arrange ---
    session_orm, session_id_str = await _create_session_with_messages(
        async_client, test_tenant, 3
    )
    session_uuid = session_orm.id

    with patch(
        "services.profile_bridge.analyze_cend_turn",
        side_effect=_fake_analyze_cend_success,
    ):
        # --- Act ---
        bridge_ran = await bridge_profile_to_session_profiles(
            session=session_orm,
            tenant_id=TEST_TENANT_ID,
            user_content="My score is 610 from Guangdong, like Math and Physics",
            assistant_content="Got it, you are from Guangdong with 610 score and science background.",
        )

    # --- Assert ---
    assert bridge_ran is True, "Bridge should return True when extraction has data"

    async with async_session() as db:
        result = await db.execute(
            select(SessionProfile).where(
                SessionProfile.tenant_id == TEST_TENANT_ID,
                SessionProfile.session_id == session_uuid,
            )
        )
        profile = result.scalar_one_or_none()
        assert profile is not None

        pj = profile.profile_json
        assert isinstance(pj, dict)

        # basic
        assert pj.get("basic", {}).get("province") == "Guangdong"
        assert pj.get("basic", {}).get("subject_type") == "Physics"
        assert pj.get("basic", {}).get("score") == 610

        # interests
        interests = pj.get("interests", {})
        assert "Math" in interests.get("preferred_subjects", [])
        assert "Physics" in interests.get("preferred_subjects", [])
        assert "Math" in interests.get("strong_subjects", [])

        # riasec
        riasec = pj.get("riasec", {})
        assert riasec.get("I") == 7
        assert riasec.get("R") == 5
        assert riasec.get("S") == 3

        # values
        assert "CS" in pj.get("values", [])
        assert "AI" in pj.get("values", [])

        # region_pref
        region = pj.get("region_pref", {})
        assert region.get("province") == "Guangdong"
        assert region.get("city") == "Guangzhou"

        # concerns
        assert "employment" in pj.get("concerns", [])

        # completeness
        assert profile.completeness == "L2"
        assert pj.get("completeness") == "L2"

        # confidence_json
        assert isinstance(profile.confidence_json, dict)

        # tenant association
        assert profile.tenant_id == TEST_TENANT_ID
        assert profile.session_id == session_uuid


# ===================================================================
# Test 3: JSON backup file written after extraction
# ===================================================================


@pytest.mark.asyncio
async def test_json_backup_file_written_after_extraction(
    async_client, test_tenant
):
    """After bridge runs, data/extracted_profiles/{session_uuid}.json exists with correct data."""
    # --- Arrange ---
    session_orm, session_id_str = await _create_session_with_messages(
        async_client, test_tenant, 3
    )
    session_uuid = session_orm.id

    import services.profile_bridge as pb_module

    backup_dir = pb_module._JSON_BACKUP_DIR
    backup_path = os.path.join(backup_dir, f"{session_uuid}.json")

    if os.path.exists(backup_path):
        os.remove(backup_path)

    with patch(
        "services.profile_bridge.analyze_cend_turn",
        side_effect=_fake_analyze_cend_success,
    ):
        # --- Act ---
        await bridge_profile_to_session_profiles(
            session=session_orm,
            tenant_id=TEST_TENANT_ID,
            user_content="Score 610 from Guangdong, physics stream",
            assistant_content="Your profile has been recorded.",
        )

    # --- Assert ---
    assert os.path.exists(backup_path), f"Backup file must exist at {backup_path}"

    with open(backup_path, "r", encoding="utf-8") as f:
        backup_data = json.load(f)

    assert isinstance(backup_data, dict)
    assert backup_data.get("basic", {}).get("province") == "Guangdong"
    assert backup_data.get("basic", {}).get("score") == 610
    assert "CS" in backup_data.get("values", [])

    # --- Cleanup ---
    try:
        os.remove(backup_path)
    except Exception:
        pass


# ===================================================================
# Test 4: Tenant isolation for session_profiles
# ===================================================================


@pytest.mark.asyncio
async def test_tenant_isolation_session_profiles(
    async_client, test_tenant, other_tenant, seed_session_profile
):
    """Tenant A cannot read Tenant B's session_profiles data via load_existing_profile_json."""
    # --- Arrange ---
    session_orm, session_id_str = await _create_session_with_messages(
        async_client, test_tenant, 3
    )
    session_uuid = session_orm.id

    profile_data = {
        "basic": {"province": "Guangdong", "score": 610},
        "riasec": {"I": 7, "R": 5},
        "values": ["CS"],
        "completeness": "L2",
    }
    await seed_session_profile(
        tenant_id=TEST_TENANT_ID,
        session_id=session_uuid,
        profile_json=profile_data,
        completeness="L2",
    )

    # Verify test_tenant CAN read its own data
    own_result = await load_existing_profile_json(TEST_TENANT_ID, session_uuid)
    assert own_result is not None, "Tenant must be able to read its own SessionProfile"
    assert own_result.get("basic", {}).get("province") == "Guangdong"

    # --- Act ---
    other_result = await load_existing_profile_json(OTHER_TENANT_ID, session_uuid)

    # --- Assert ---
    assert other_result is None, "Tenant B must NOT read Tenant A session_profiles"

    # Verify at DB level
    async with async_session() as db:
        result = await db.execute(
            select(SessionProfile).where(
                SessionProfile.tenant_id == OTHER_TENANT_ID,
                SessionProfile.session_id == session_uuid,
            )
        )
        assert result.scalar_one_or_none() is None

    # Confirm row still exists for test_tenant
    async with async_session() as db:
        result = await db.execute(
            select(SessionProfile).where(
                SessionProfile.tenant_id == TEST_TENANT_ID,
                SessionProfile.session_id == session_uuid,
            )
        )
        assert result.scalar_one_or_none() is not None
