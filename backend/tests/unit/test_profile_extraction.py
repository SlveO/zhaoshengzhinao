"""Pipeline stage: Profile Extraction — regex-based extraction of province, subject, score from chat text."""

import pytest

from services.consult_service import extract_profile_from_message


class TestExtractProvince:
    """Pipeline stage: Profile Extraction — province detection from text."""

    @pytest.mark.asyncio
    async def test_extract_province_from_user_message(self):
        """Province name appearing in user content is extracted."""
        updates = await extract_profile_from_message(
            "我是广东的考生", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["province"] == "广东"

    @pytest.mark.asyncio
    async def test_extract_province_from_ai_response(self):
        """Province name appearing in AI response is also extracted."""
        updates = await extract_profile_from_message(
            "你好", "你是广东的考生对吧？", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["province"] == "广东"

    @pytest.mark.asyncio
    async def test_no_duplicate_province_when_already_known(self):
        """If province is already in profile, it is not re-extracted."""
        updates = await extract_profile_from_message(
            "我是广东的", "", {"province": "广东", "subject_type": "", "score": 0}
        )
        assert "province" not in updates

    @pytest.mark.asyncio
    async def test_extract_province_beijing(self):
        updates = await extract_profile_from_message(
            "北京考生", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["province"] == "北京"

    @pytest.mark.asyncio
    async def test_extract_province_sichuan(self):
        updates = await extract_profile_from_message(
            "四川成都的", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["province"] == "四川"


class TestExtractSubjectType:
    """Pipeline stage: Profile Extraction — subject_type (物理类/历史类) detection."""

    @pytest.mark.asyncio
    async def test_extract_wuli_from_physics_keyword(self):
        """Keyword '物理' maps to 物理类."""
        updates = await extract_profile_from_message(
            "我选了物理", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["subject_type"] == "物理类"

    @pytest.mark.asyncio
    async def test_extract_wuli_from_science_keyword(self):
        """Keyword '理科' maps to 物理类."""
        updates = await extract_profile_from_message(
            "理科生", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["subject_type"] == "物理类"

    @pytest.mark.asyncio
    async def test_extract_lishi_from_history_keyword(self):
        """Keyword '历史' maps to 历史类."""
        updates = await extract_profile_from_message(
            "我选的历史", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["subject_type"] == "历史类"

    @pytest.mark.asyncio
    async def test_extract_lishi_from_arts_keyword(self):
        """Keyword '文科' maps to 历史类."""
        updates = await extract_profile_from_message(
            "我是文科生", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["subject_type"] == "历史类"

    @pytest.mark.asyncio
    async def test_physics_takes_priority_over_history(self):
        """When both 物理 and 历史 appear, 物理 is checked first and wins."""
        updates = await extract_profile_from_message(
            "我物理和历史都学了但选了物理", "",
            {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["subject_type"] == "物理类"

    @pytest.mark.asyncio
    async def test_no_duplicate_subject_when_already_known(self):
        updates = await extract_profile_from_message(
            "物理", "", {"province": "", "subject_type": "物理类", "score": 0}
        )
        assert "subject_type" not in updates


class TestExtractScore:
    """Pipeline stage: Profile Extraction — score (3-digit + 分) detection."""

    @pytest.mark.asyncio
    async def test_extract_score_from_user_message(self):
        """Pattern '600分' extracts score=600."""
        updates = await extract_profile_from_message(
            "我考了600分", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["score"] == 600

    @pytest.mark.asyncio
    async def test_extract_score_from_ai_response(self):
        """Score pattern in AI response is also extracted."""
        updates = await extract_profile_from_message(
            "你好", "你的分数是620分对吧", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["score"] == 620

    @pytest.mark.asyncio
    async def test_no_duplicate_score_when_already_known(self):
        updates = await extract_profile_from_message(
            "我考了700分", "", {"province": "", "subject_type": "", "score": 600}
        )
        assert "score" not in updates

    @pytest.mark.asyncio
    async def test_score_with_spaces(self):
        """Score regex matches '600 分' with whitespace."""
        updates = await extract_profile_from_message(
            "我考了 600 分", "", {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["score"] == 600

    @pytest.mark.asyncio
    async def test_no_false_score_from_year(self):
        """Year-like numbers (2024年) should not match as scores since they are 4 digits."""
        updates = await extract_profile_from_message(
            "2024年高考", "", {"province": "", "subject_type": "", "score": 0}
        )
        # 2024 is 4 digits, regex is \d{3} so it won't match
        assert "score" not in updates


class TestCombinedExtraction:
    """Pipeline stage: Profile Extraction — multiple fields extracted simultaneously."""

    @pytest.mark.asyncio
    async def test_extract_all_three_fields_at_once(self):
        """Province, subject, and score can all be extracted from a single message."""
        updates = await extract_profile_from_message(
            "我是广东物理类考生，高考620分", "",
            {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["province"] == "广东"
        assert updates["subject_type"] == "物理类"
        assert updates["score"] == 620

    @pytest.mark.asyncio
    async def test_partial_extraction_only_fills_missing(self):
        """Only empty profile fields are filled; existing ones are preserved."""
        updates = await extract_profile_from_message(
            "我物理620分", "",
            {"province": "广东", "subject_type": "", "score": 0}
        )
        assert "province" not in updates
        assert updates["subject_type"] == "物理类"
        assert updates["score"] == 620

    @pytest.mark.asyncio
    async def test_no_extraction_when_nothing_matches(self):
        """Returns empty dict when no recognizable patterns are found."""
        updates = await extract_profile_from_message(
            "你好，我想了解一下学校情况", "",
            {"province": "", "subject_type": "", "score": 0}
        )
        assert updates == {}

    @pytest.mark.asyncio
    async def test_extract_from_combined_user_and_ai_text(self):
        """Extraction searches across both user message and AI response combined."""
        updates = await extract_profile_from_message(
            "我想学计算机", "同学你好，你是广东的考生吗？分数是多少呢？",
            {"province": "", "subject_type": "", "score": 0}
        )
        assert updates["province"] == "广东"


class TestExtractIntentMajors:
    """extract_profile_from_message 的意向专业关键字提取"""

    @pytest.mark.asyncio
    async def test_extract_intent_majors_from_user_message(self):
        """用户消息中含"计算机" → 提取到 intent_majors"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message("我对计算机很感兴趣", "", {})
        assert updates.get("intent_majors") == ["计算机"]

    @pytest.mark.asyncio
    async def test_extract_multiple_intent_majors(self):
        """多个关键字 → 全部提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message("我想学计算机和人工智能", "", {})
        majors = updates.get("intent_majors", [])
        assert "计算机" in majors
        assert "人工智能" in majors

    @pytest.mark.asyncio
    async def test_no_duplicate_intent_when_already_known(self):
        """已有 intent_majors → 跳过提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message(
            "我对金融感兴趣", "", {"intent_majors": ["计算机"]}
        )
        assert "intent_majors" not in updates

    @pytest.mark.asyncio
    async def test_no_intent_when_no_keyword_matches(self):
        """无专业关键字 → updates 不含 intent_majors"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message("你好，今天天气不错", "", {})
        assert "intent_majors" not in updates

    @pytest.mark.asyncio
    async def test_extract_intent_majors_capped_at_five(self):
        """超过 5 个关键字 → 截断为 5"""
        from services.consult_service import extract_profile_from_message
        text = "计算机 人工智能 软件工程 金融 法学 医学 数学"
        updates = await extract_profile_from_message(text, "", {})
        assert len(updates.get("intent_majors", [])) <= 5

    @pytest.mark.asyncio
    async def test_extract_intent_from_ai_response(self):
        """AI 回复中的关键字也被提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message(
            "我想学计算机",
            "华师计算机专业很好，人工智能方向也很强",
            {},
        )
        majors = updates.get("intent_majors", [])
        assert "计算机" in majors
        assert "人工智能" in majors

    @pytest.mark.asyncio
    async def test_extract_all_four_fields_together(self):
        """省份+科类+分数+意向专业 同时提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message(
            "广东物理类 620 分想学计算机和人工智能", "", {}
        )
        assert updates.get("province") == "广东"
        assert updates.get("subject_type") == "物理类"
        assert updates.get("score") == 620
        majors = updates.get("intent_majors", [])
        assert "计算机" in majors
        assert "人工智能" in majors

    @pytest.mark.asyncio
    async def test_extract_intent_majors_empty_list_skipped(self):
        """空列表 intent_majors 是 falsy → 触发提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message(
            "我考虑学计算机", "", {"intent_majors": []}
        )
        assert updates.get("intent_majors") == ["计算机"]
