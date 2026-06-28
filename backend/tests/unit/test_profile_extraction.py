"""Pipeline stage: Profile Extraction — intent_majors extraction from chat text.

Note: Province/subjects/score/rank are now collected via mini-app form (BasicInfoRequest),
not via AI extraction. Only intent_majors are extracted from chat text.
"""

import pytest

from services.consult_service import extract_profile_from_message


class TestExtractIntentMajors:
    """Pipeline stage: Profile Extraction — intent major detection from text."""

    @pytest.mark.asyncio
    async def test_extract_cs_from_user_message(self):
        """Keyword '计算机' maps to intent_majors."""
        updates = await extract_profile_from_message(
            "我想学计算机", "", {"intent_majors": []}
        )
        assert updates.get("intent_majors") == ["计算机"]

    @pytest.mark.asyncio
    async def test_extract_ai_from_response(self):
        """Keywords in AI response are also extracted."""
        updates = await extract_profile_from_message(
            "你好", "你对人工智能感兴趣吗？", {"intent_majors": []}
        )
        assert updates.get("intent_majors") == ["人工智能"]

    @pytest.mark.asyncio
    async def test_no_duplicate_when_already_known(self):
        """If intent_majors already populated, do not re-extract."""
        updates = await extract_profile_from_message(
            "我想学计算机", "", {"intent_majors": ["软件工程"]}
        )
        assert "intent_majors" not in updates

    @pytest.mark.asyncio
    async def test_multiple_majors_extracted(self):
        """Multiple matching keywords are all collected."""
        updates = await extract_profile_from_message(
            "我对计算机和法学都感兴趣", "", {"intent_majors": []}
        )
        assert "计算机" in updates["intent_majors"]
        assert "法学" in updates["intent_majors"]

    @pytest.mark.asyncio
    async def test_max_five_majors(self):
        """At most 5 majors are kept (slice [:5])."""
        updates = await extract_profile_from_message(
            "计算机 人工智能 软件工程 数据科学 网络安全 大数据 数学 物理",
            "", {"intent_majors": []}
        )
        assert len(updates["intent_majors"]) <= 5

    @pytest.mark.asyncio
    async def test_no_extraction_when_nothing_matches(self):
        """Returns empty dict when no recognizable patterns are found."""
        updates = await extract_profile_from_message(
            "你好，我想了解一下学校情况", "", {"intent_majors": []}
        )
        assert updates == {}
