"""Unit tests for topic_cloud — contract-driven black-box tests.

Based on docs/contracts/analytics_consumption_contract.md.
Does NOT read implementation code; tests against public interface signatures only.
"""

import uuid

import pytest

from analytics.topic_cloud import get_topic_cloud
from tests.conftest import TEST_TENANT_ID, OTHER_TENANT_ID


# ---------------------------------------------------------------------------
# get_topic_cloud
# ---------------------------------------------------------------------------


class TestGetTopicCloud:
    @pytest.mark.asyncio
    async def test_concerns_weighted_x2(self, setup_db, test_tenant, seed_event, seed_session_profile):
        # Contract 1: concerns present → weighted x2
        # Arrange — seed a concern word that also appears in chat (to verify x2 boost)
        await seed_session_profile(
            tenant_id=test_tenant.id,
            profile_json={"concerns": ["人工智能"]},
        )
        # Seed chat message containing "人工智能" once (weight x1)
        await seed_event(
            "chat.message_sent",
            tenant_id=test_tenant.id,
            payload={"content": "我对人工智能感兴趣"},
        )
        # Act
        result = await get_topic_cloud(str(test_tenant.id), days=30)
        # Assert — find 人工智能, its count should be >= 2 (concerns x2)
        # (may also get x1 from chat, total could be 3)
        ai_entry = next((r for r in result if r["word"] == "人工智能"), None)
        assert ai_entry is not None
        assert ai_entry["count"] >= 2

    @pytest.mark.asyncio
    async def test_no_concerns_returns_only_normal_word_freq(self, setup_db, test_tenant, seed_event):
        # Contract 2: no concerns → only normal word freq (x1)
        # Arrange — no session_profiles, only chat messages
        await seed_event(
            "chat.message_sent",
            tenant_id=test_tenant.id,
            payload={"content": "计算机专业就业前景"},
        )
        # Act
        result = await get_topic_cloud(str(test_tenant.id), days=30)
        # Assert — returns list of dicts with word/count
        assert isinstance(result, list)
        for item in result:
            assert "word" in item
            assert "count" in item
            assert item["count"] >= 1

    @pytest.mark.asyncio
    async def test_empty_concerns_array_skipped(self, setup_db, test_tenant, seed_session_profile):
        # Contract 3: concerns empty array → skipped, no error
        # Arrange
        await seed_session_profile(
            tenant_id=test_tenant.id,
            profile_json={"concerns": []},
        )
        # Act — should not raise
        result = await get_topic_cloud(str(test_tenant.id), days=30)
        # Assert
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_returns_top_n_sorted_by_count(self, setup_db, test_tenant, seed_event):
        # Contract 4: returns Top N sorted by count descending
        # Arrange — seed multiple messages with different word frequencies
        for _ in range(5):
            await seed_event(
                "chat.message_sent",
                tenant_id=test_tenant.id,
                payload={"content": "计算机计算机计算机"},
            )
        for _ in range(2):
            await seed_event(
                "chat.message_sent",
                tenant_id=test_tenant.id,
                payload={"content": "电子工程"},
            )
        # Act
        result = await get_topic_cloud(str(test_tenant.id), days=30)
        # Assert — sorted descending
        counts = [item["count"] for item in result]
        assert counts == sorted(counts, reverse=True)
        # Top 50 max
        assert len(result) <= 50

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, setup_db, test_tenant, other_tenant, seed_event, seed_session_profile):
        # Contract 5: tenant isolation — only current tenant's data
        # Arrange — seed data for test_tenant
        await seed_session_profile(
            tenant_id=test_tenant.id,
            profile_json={"concerns": ["测试租户词"]},
        )
        # Seed data for other_tenant
        await seed_session_profile(
            tenant_id=other_tenant.id,
            profile_json={"concerns": ["其他租户词"]},
        )
        # Act — query test_tenant
        result = await get_topic_cloud(str(test_tenant.id), days=30)
        words = [item["word"] for item in result]
        # Assert — test_tenant's concern visible, other_tenant's not
        assert "测试租户词" in words
        assert "其他租户词" not in words

    @pytest.mark.asyncio
    async def test_no_data_returns_empty_list(self, setup_db, test_tenant):
        # Boundary: no data at all → empty list (not error)
        result = await get_topic_cloud(str(test_tenant.id), days=30)
        assert result == []
