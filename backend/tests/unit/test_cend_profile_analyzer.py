"""Unit tests for cend_profile_analyzer — pure logic, no I/O."""
import pytest
from services.cend_profile_analyzer import (
    CendExtractionResult,
    parse_cend_response,
    merge_extraction_results,
    _compute_completeness,
    _summarize_existing,
    build_cend_analysis_prompt,
    RIASEC_KEYS,
)


class TestCendExtractionResult:
    def test_default_result_is_empty(self):
        r = CendExtractionResult()
        assert r.completeness == "L1"
        assert r.has_any_data() is False

    def test_to_profile_json_includes_all_fields(self):
        r = CendExtractionResult()
        j = r.to_profile_json()
        for key in ("basic", "interests", "concerns", "riasec", "values", "region_pref", "extra", "completeness"):
            assert key in j

    def test_has_any_data_with_province(self):
        r = CendExtractionResult()
        r.basic["province"] = "广东"
        assert r.has_any_data() is True

    def test_has_any_data_with_riasec(self):
        r = CendExtractionResult()
        r.riasec["R"] = 7
        assert r.has_any_data() is True

    def test_has_any_data_with_concerns(self):
        r = CendExtractionResult()
        r.concerns = ["担心"]
        assert r.has_any_data() is True


class TestParseCendResponse:
    def test_parse_valid_json_populates_all_fields(self):
        raw = '{"basic":{"province":"广东","subject_type":"物理类","score":600},"riasec":{"R":7,"I":8,"A":0,"S":5,"E":6,"C":0},"values":["个人成长"],"concerns":["担心考不上"],"region_pref":{"province":"广东","city":"广州"}}'
        parsed = parse_cend_response(raw)
        assert parsed.basic["province"] == "广东"
        assert parsed.basic["score"] == 600
        assert parsed.riasec["R"] == 7
        assert parsed.riasec["C"] == 0
        assert parsed.values == ["个人成长"]
        assert parsed.region_pref["city"] == "广州"

    def test_parse_strips_markdown_code_block(self):
        raw = '```json\n{"basic":{"province":"北京"},"riasec":{"R":5,"I":6,"A":0,"S":0,"E":0,"C":0}}\n```'
        parsed = parse_cend_response(raw)
        assert parsed.basic["province"] == "北京"
        assert parsed.riasec["R"] == 5

    def test_parse_strips_markdown_no_lang_tag(self):
        raw = '```\n{"basic":{"province":"上海"},"riasec":{"R":0,"I":0,"A":0,"S":0,"E":0,"C":0}}\n```'
        parsed = parse_cend_response(raw)
        assert parsed.basic["province"] == "上海"

    def test_parse_garbage_returns_default(self):
        parsed = parse_cend_response("not json at all")
        assert parsed.has_any_data() is False
        assert parsed.completeness == "L1"

    def test_parse_empty_string_returns_default(self):
        parsed = parse_cend_response("")
        assert parsed.has_any_data() is False

    def test_parse_none_returns_default(self):
        parsed = parse_cend_response(None)
        assert parsed.has_any_data() is False

    def test_parse_string_score_converted_to_int(self):
        raw = '{"basic":{"score":"600"}}'
        parsed = parse_cend_response(raw)
        assert parsed.basic["score"] == 600

    def test_parse_rejects_invalid_riasec_values(self):
        raw = '{"riasec":{"R":15,"I":-1,"A":"abc"}}'
        parsed = parse_cend_response(raw)
        assert parsed.riasec["R"] == 0
        assert parsed.riasec["I"] == 0
        assert parsed.riasec["A"] == 0

    def test_parse_partial_json_fills_defaults(self):
        raw = '{"basic":{"province":"广东"}}'
        parsed = parse_cend_response(raw)
        assert parsed.basic["province"] == "广东"
        assert parsed.basic["score"] is None
        assert parsed.has_any_data() is True

    def test_parse_non_dict_returns_default(self):
        parsed = parse_cend_response('[1, 2, 3]')
        assert parsed.has_any_data() is False


class TestComputeCompleteness:
    def test_l3_with_4_riasec_and_values(self):
        r = CendExtractionResult()
        r.riasec = {"R": 7, "I": 8, "A": 5, "S": 6, "E": 0, "C": 0}
        r.values = ["个人成长"]
        assert _compute_completeness(r) == "L3"

    def test_l2_with_2_riasec_and_region(self):
        r = CendExtractionResult()
        r.riasec = {"R": 7, "I": 8, "A": 0, "S": 0, "E": 0, "C": 0}
        r.region_pref = {"province": "广东", "city": None}
        assert _compute_completeness(r) == "L2"

    def test_l2_with_city_only(self):
        r = CendExtractionResult()
        r.riasec = {"R": 7, "I": 0, "A": 8, "S": 0, "E": 0, "C": 0}
        r.region_pref = {"province": None, "city": "广州"}
        assert _compute_completeness(r) == "L2"

    def test_l1_with_no_data(self):
        r = CendExtractionResult()
        assert _compute_completeness(r) == "L1"

    def test_l1_with_3_riasec_but_no_values_or_region(self):
        r = CendExtractionResult()
        r.riasec = {"R": 7, "I": 8, "A": 5, "S": 0, "E": 0, "C": 0}
        assert _compute_completeness(r) == "L1"


class TestMergeExtractionResults:
    def test_merge_scalar_new_overrides_old(self):
        existing = CendExtractionResult()
        existing.basic["province"] = "广东"
        existing.basic["score"] = 550

        new_ext = CendExtractionResult()
        new_ext.basic["province"] = "北京"
        new_ext.basic["score"] = 600

        merged = merge_extraction_results(existing, new_ext)
        assert merged.basic["province"] == "北京"
        assert merged.basic["score"] == 600

    def test_merge_scalar_new_none_keeps_old(self):
        existing = CendExtractionResult()
        existing.basic["province"] = "广东"

        new_ext = CendExtractionResult()
        # province is None

        merged = merge_extraction_results(existing, new_ext)
        assert merged.basic["province"] == "广东"

    def test_merge_riasec_nonzero_override(self):
        existing = CendExtractionResult()
        existing.riasec["R"] = 7
        existing.riasec["I"] = 5

        new_ext = CendExtractionResult()
        new_ext.riasec["R"] = 9  # override
        new_ext.riasec["A"] = 6  # new dimension
        new_ext.riasec["I"] = 0  # 0 = not mentioned, keep old

        merged = merge_extraction_results(existing, new_ext)
        assert merged.riasec["R"] == 9
        assert merged.riasec["I"] == 5  # preserved
        assert merged.riasec["A"] == 6  # added

    def test_merge_concerns_dedup(self):
        existing = CendExtractionResult()
        existing.concerns = ["担心考不上", "不知道选什么专业"]

        new_ext = CendExtractionResult()
        new_ext.concerns = ["不知道选什么专业", "怕滑档"]

        merged = merge_extraction_results(existing, new_ext)
        assert merged.concerns == ["担心考不上", "不知道选什么专业", "怕滑档"]

    def test_merge_values_dedup(self):
        existing = CendExtractionResult()
        existing.values = ["个人成长", "薪资水平"]

        new_ext = CendExtractionResult()
        new_ext.values = ["薪资水平", "社会贡献"]

        merged = merge_extraction_results(existing, new_ext)
        assert merged.values == ["个人成长", "薪资水平", "社会贡献"]

    def test_merge_interests_dedup(self):
        existing = CendExtractionResult()
        existing.interests["preferred_subjects"] = ["数学", "物理"]

        new_ext = CendExtractionResult()
        new_ext.interests["preferred_subjects"] = ["物理", "计算机"]

        merged = merge_extraction_results(existing, new_ext)
        assert merged.interests["preferred_subjects"] == ["数学", "物理", "计算机"]

    def test_merge_recomputes_completeness(self):
        existing = CendExtractionResult()
        existing.riasec = {"R": 7, "I": 8, "A": 0, "S": 0, "E": 0, "C": 0}
        existing.region_pref = {"province": "广东", "city": None}
        existing.completeness = "L2"

        new_ext = CendExtractionResult()
        new_ext.riasec = {"A": 5, "S": 6}
        new_ext.values = ["个人成长"]

        merged = merge_extraction_results(existing, new_ext)
        assert merged.completeness == "L3"

    def test_merge_extra_shallow(self):
        existing = CendExtractionResult()
        existing.extra = {"a": 1, "b": 2}

        new_ext = CendExtractionResult()
        new_ext.extra = {"b": 99, "c": 3}

        merged = merge_extraction_results(existing, new_ext)
        assert merged.extra == {"a": 1, "b": 99, "c": 3}

    def test_merge_region_pref_override(self):
        existing = CendExtractionResult()
        existing.region_pref["province"] = "广东"
        existing.region_pref["city"] = "广州"

        new_ext = CendExtractionResult()
        new_ext.region_pref["province"] = "北京"
        # city stays None

        merged = merge_extraction_results(existing, new_ext)
        assert merged.region_pref["province"] == "北京"
        assert merged.region_pref["city"] == "广州"


class TestSummarizeExisting:
    def test_none_profile_returns_placeholder(self):
        summary = _summarize_existing(None)
        assert "暂无" in summary

    def test_empty_profile_returns_placeholder(self):
        summary = _summarize_existing({})
        assert "暂无" in summary

    def test_full_profile_includes_all_sections(self):
        profile = {
            "basic": {"province": "广东", "subject_type": "物理类", "score": 600},
            "interests": {"preferred_subjects": ["数学", "物理"]},
            "riasec": {"R": 7, "I": 8},
            "values": ["个人成长"],
            "concerns": ["担心考不上"],
            "region_pref": {"province": "广东", "city": "广州"},
        }
        summary = _summarize_existing(profile)
        assert "广东" in summary
        assert "物理类" in summary
        assert "600" in summary
        assert "R(" in summary or "动手操作" in summary
        assert "个人成长" in summary
        assert "担心考不上" in summary
        assert "广州" in summary


class TestBuildPrompt:
    def test_prompt_includes_user_msg_and_ai_reply(self):
        prompt = build_cend_analysis_prompt("我想学计算机", "计算机前景很好", None)
        assert "我想学计算机" in prompt
        assert "计算机前景很好" in prompt

    def test_prompt_format_replaces_placeholder(self):
        prompt = build_cend_analysis_prompt("x", "y", {"basic": {"province": "广东"}})
        assert "广东" in prompt
        assert "existing_profile_summary" not in prompt


class TestDedupMergeLists:
    def test_dedup_preserves_order(self):
        from services.cend_profile_analyzer import _dedup_merge_lists
        result = _dedup_merge_lists(["a", "b", "c"], ["b", "d", "a"])
        assert result == ["a", "b", "c", "d"]
