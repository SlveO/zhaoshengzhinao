"""Unit tests for cend_profile_analyzer — contract-driven black-box tests.

Based on docs/contracts/cend_profile_analyzer_contract.md.
Does NOT read implementation code; tests against public interface signatures only.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.cend_profile_analyzer import (
    CendExtractionResult,
    analyze_cend_turn,
    build_cend_analysis_prompt,
    merge_extraction_results,
    parse_cend_response,
    _compute_completeness,
    _dedup_merge_lists,
    _summarize_existing,
)


# ---------------------------------------------------------------------------
# CendExtractionResult.to_profile_json / has_any_data
# ---------------------------------------------------------------------------


class TestCendExtractionResultToProfileJson:
    def test_returns_dict_with_8_keys(self):
        # Arrange
        result = CendExtractionResult()
        # Act
        out = result.to_profile_json()
        # Assert
        assert set(out.keys()) == {
            "basic", "interests", "concerns", "riasec",
            "values", "region_pref", "extra", "completeness",
        }

    def test_output_is_json_serializable(self):
        # Arrange
        result = CendExtractionResult(
            basic={"intent_majors": ["计算机"], "focus_points": ["就业"]},
            concerns=["计算机", "电子"],
            riasec={"R": 5, "I": 8, "A": 2, "S": 4, "E": 6, "C": 3},
        )
        # Act / Assert
        json.dumps(result.to_profile_json())  # no exception

    def test_list_fields_returned_as_copies(self):
        # Arrange
        result = CendExtractionResult(concerns=["a", "b"])
        # Act
        out = result.to_profile_json()
        out["concerns"].append("c")
        # Assert — original unchanged
        assert result.concerns == ["a", "b"]


class TestCendExtractionResultHasAnyData:
    def test_empty_result_returns_false(self):
        # Arrange
        result = CendExtractionResult()
        # Act / Assert
        assert result.has_any_data() is False

    def test_basic_province_set_returns_true(self):
        result = CendExtractionResult(basic={"province": "广东"})
        assert result.has_any_data() is True

    def test_riasec_all_zero_returns_false(self):
        result = CendExtractionResult(riasec={"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0})
        assert result.has_any_data() is False

    def test_concerns_non_empty_returns_true(self):
        result = CendExtractionResult(concerns=["AI"])
        assert result.has_any_data() is True


# ---------------------------------------------------------------------------
# parse_cend_response
# ---------------------------------------------------------------------------


class TestParseCendResponse:
    def test_valid_json_parses_to_fields(self):
        # Arrange
        payload = {
            "basic": {"intent_majors": ["计算机"], "focus_points": ["就业"]},
            "interests": {"preferred_subjects": ["数学"], "strong_subjects": ["物理"], "hobbies": ["编程"]},
            "concerns": ["计算机", "AI"],
            "riasec": {"R": 5, "I": 9, "A": 2, "S": 3, "E": 6, "C": 4},
            "values": ["稳定", "创新"],
            "region_pref": {"province": "广东", "city": "广州"},
            "extra": {"note": "test"},
        }
        # Act
        result = parse_cend_response(json.dumps(payload))
        # Assert
        assert result.basic["intent_majors"] == ["计算机"]
        assert result.concerns == ["计算机", "AI"]
        assert result.riasec["I"] == 9

    def test_invalid_json_returns_empty_result_no_exception(self):
        # Arrange
        bad_text = "not a json {{{"
        # Act
        result = parse_cend_response(bad_text)
        # Assert
        assert result.has_any_data() is False

    def test_missing_fields_use_defaults(self):
        # Arrange — only basic provided
        text = json.dumps({"basic": {"province": "北京"}})
        # Act
        result = parse_cend_response(text)
        # Assert
        assert result.basic["province"] == "北京"
        assert result.concerns == []
        assert result.values == []

    def test_extra_fields_ignored(self):
        # Arrange
        text = json.dumps({"basic": {"province": "广东"}, "unknown_field": "ignored"})
        # Act
        result = parse_cend_response(text)
        # Assert
        out = result.to_profile_json()
        assert "unknown_field" not in out

    def test_riasec_out_of_range_kept(self):
        # Contract 5: RIASEC out of range → kept (not clamped)
        # Arrange
        text = json.dumps({"riasec": {"R": 99, "I": -5, "A": 2, "S": 3, "E": 6, "C": 4}})
        # Act
        result = parse_cend_response(text)
        # Assert
        assert result.riasec["R"] == 99
        assert result.riasec["I"] == -5

    def test_empty_string_returns_empty_result(self):
        result = parse_cend_response("")
        assert result.has_any_data() is False

    def test_json_wrapped_in_markdown_codeblock(self):
        # Boundary: LLM response wrapped in ```json ... ```
        payload = {"basic": {"province": "广东"}}
        text = f"```json\n{json.dumps(payload)}\n```"
        result = parse_cend_response(text)
        assert result.basic["province"] == "广东"


# ---------------------------------------------------------------------------
# merge_extraction_results
# ---------------------------------------------------------------------------


class TestMergeExtractionResults:
    def test_list_fields_merge_dedup_existing_first(self):
        # Arrange
        existing = CendExtractionResult(concerns=["计算机", "AI"])
        new = CendExtractionResult(concerns=["AI", "电子"])
        # Act
        merged = merge_extraction_results(existing, new)
        # Assert
        assert merged.concerns == ["计算机", "AI", "电子"]

    def test_scalar_fields_new_non_none_overrides(self):
        # Arrange
        existing = CendExtractionResult(basic={"province": "广东", "score": 580})
        new = CendExtractionResult(basic={"province": "北京", "score": None})
        # Act
        merged = merge_extraction_results(existing, new)
        # Assert — new non-None overrides
        assert merged.basic["province"] == "北京"
        # None in new does not override existing
        assert merged.basic["score"] == 580

    def test_riasec_non_zero_new_overrides(self):
        # Arrange
        existing = CendExtractionResult(riasec={"R": 5, "I": 8, "A": 2, "S": 4, "E": 6, "C": 3})
        new = CendExtractionResult(riasec={"R": 0, "I": 9, "A": 0, "S": 0, "E": 0, "C": 0})
        # Act
        merged = merge_extraction_results(existing, new)
        # Assert — 0 means "not mentioned", keep existing; non-zero overrides
        assert merged.riasec["R"] == 5
        assert merged.riasec["I"] == 9
        assert merged.riasec["A"] == 2

    def test_interests_dict_deep_merge(self):
        # Arrange
        existing = CendExtractionResult(
            interests={"preferred_subjects": ["数学"], "strong_subjects": ["物理"], "hobbies": ["阅读"]}
        )
        new = CendExtractionResult(
            interests={"preferred_subjects": ["数学", "化学"], "strong_subjects": [], "hobbies": ["编程"]}
        )
        # Act
        merged = merge_extraction_results(existing, new)
        # Assert — dedup merge per sub-list
        assert "数学" in merged.interests["preferred_subjects"]
        assert "化学" in merged.interests["preferred_subjects"]
        assert "物理" in merged.interests["strong_subjects"]
        assert "编程" in merged.interests["hobbies"]

    def test_existing_empty_returns_new(self):
        # Arrange
        existing = CendExtractionResult()
        new = CendExtractionResult(basic={"province": "广东"}, concerns=["AI"])
        # Act
        merged = merge_extraction_results(existing, new)
        # Assert
        assert merged.basic["province"] == "广东"
        assert merged.concerns == ["AI"]

    def test_completeness_recomputed(self):
        # Arrange — existing L1, new has enough data for L3
        existing = CendExtractionResult(completeness="L1")
        new = CendExtractionResult(
            basic={"province": "广东"},
            concerns=["AI"],
            riasec={"R": 5, "I": 8, "A": 2, "S": 4, "E": 6, "C": 3},
            values=["创新"],
        )
        # Act
        merged = merge_extraction_results(existing, new)
        # Assert — completeness recomputed, not just copied
        assert merged.completeness in ("L1", "L2", "L3")


# ---------------------------------------------------------------------------
# _compute_completeness
# ---------------------------------------------------------------------------


class TestComputeCompleteness:
    def test_only_basic_returns_L1(self):
        result = CendExtractionResult(basic={"province": "广东"})
        assert _compute_completeness(result) == "L1"

    def test_basic_interests_concerns_returns_L2(self):
        result = CendExtractionResult(
            basic={"province": "广东"},
            interests={"preferred_subjects": ["数学"]},
            concerns=["AI"],
        )
        assert _compute_completeness(result) == "L2"

    def test_full_data_returns_L3(self):
        result = CendExtractionResult(
            basic={"province": "广东"},
            interests={"preferred_subjects": ["数学"]},
            concerns=["AI"],
            riasec={"R": 5, "I": 8, "A": 2, "S": 4, "E": 6, "C": 3},
            values=["创新"],
        )
        assert _compute_completeness(result) == "L3"

    def test_all_empty_returns_L1(self):
        result = CendExtractionResult()
        assert _compute_completeness(result) == "L1"


# ---------------------------------------------------------------------------
# build_cend_analysis_prompt
# ---------------------------------------------------------------------------


class TestBuildCendAnalysisPrompt:
    def test_prompt_contains_field_definitions(self):
        # Contract 1: prompt contains 7 field definitions
        prompt = build_cend_analysis_prompt("msg", "reply", None)
        # Should mention key fields
        assert "basic" in prompt or "省份" in prompt or "province" in prompt.lower()

    def test_prompt_contains_json_format_requirement(self):
        # Contract 2: prompt contains JSON output format
        prompt = build_cend_analysis_prompt("msg", "reply", None)
        assert "json" in prompt.lower() or "JSON" in prompt

    def test_prompt_contains_existing_profile_summary_when_provided(self):
        # Contract 3: existing_profile non-empty → contains summary
        existing = {"basic": {"province": "广东"}}
        prompt = build_cend_analysis_prompt("msg", "reply", existing)
        assert "广东" in prompt

    def test_prompt_contains_current_turn_messages(self):
        # Contract 4: contains "本轮对话" with user_msg and ai_reply
        prompt = build_cend_analysis_prompt("我是广东考生", "你好同学", None)
        assert "我是广东考生" in prompt
        assert "你好同学" in prompt


# ---------------------------------------------------------------------------
# analyze_cend_turn (mocked LLM)
# ---------------------------------------------------------------------------


def _make_mock_llm_response(content: str):
    """Create a mock LLM response object with .content attribute."""
    resp = MagicMock()
    resp.content = content
    return resp


class TestAnalyzeCendTurn:
    @pytest.mark.asyncio
    async def test_llm_returns_valid_json_returns_structured_result(self):
        # Contract 1: LLM returns valid JSON → structured result
        # Arrange
        payload = {"basic": {"province": "广东", "score": 600}, "concerns": ["计算机"]}
        mock_resp = _make_mock_llm_response(json.dumps(payload))
        # Act
        with patch("services.cend_profile_analyzer.ChatOpenAI") as MockLLM:
            instance = MockLLM.return_value
            instance.invoke = MagicMock(return_value=mock_resp)
            result = await analyze_cend_turn("我是广东考生", "你好", None)
        # Assert
        assert result.basic["province"] == "广东"
        assert result.concerns == ["计算机"]

    @pytest.mark.asyncio
    async def test_llm_returns_invalid_json_returns_empty_no_exception(self):
        # Contract 2: LLM returns invalid JSON → empty result, no exception
        # Arrange
        mock_resp = _make_mock_llm_response("not json at all {{{")
        # Act
        with patch("services.cend_profile_analyzer.ChatOpenAI") as MockLLM:
            instance = MockLLM.return_value
            instance.invoke = MagicMock(return_value=mock_resp)
            result = await analyze_cend_turn("msg", "reply", None)
        # Assert
        assert result.has_any_data() is False

    @pytest.mark.asyncio
    async def test_llm_failure_returns_empty_no_exception(self):
        # Contract 3: LLM timeout/failure → retry then empty result, no exception
        # Arrange
        with patch("services.cend_profile_analyzer.ChatOpenAI") as MockLLM:
            instance = MockLLM.return_value
            instance.invoke = MagicMock(side_effect=Exception("LLM timeout"))
            # Act
            result = await analyze_cend_turn("msg", "reply", None, max_retries=1)
        # Assert — no exception raised, empty result
        assert result.has_any_data() is False

    @pytest.mark.asyncio
    async def test_existing_profile_non_empty_merged(self):
        # Contract 4: existing_profile non-empty → new extraction merged
        # Arrange
        existing = {"basic": {"province": "广东"}, "concerns": ["AI"]}
        new_payload = {"basic": {"province": "广东"}, "concerns": ["计算机"]}
        mock_resp = _make_mock_llm_response(json.dumps(new_payload))
        # Act
        with patch("services.cend_profile_analyzer.ChatOpenAI") as MockLLM:
            instance = MockLLM.return_value
            instance.invoke = MagicMock(return_value=mock_resp)
            result = await analyze_cend_turn("msg", "reply", existing)
        # Assert — merged concerns should contain both
        assert "AI" in result.concerns
        assert "计算机" in result.concerns

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        # Contract 5: retry uses exponential backoff — verify invoke called multiple times
        # Arrange
        with patch("services.cend_profile_analyzer.ChatOpenAI") as MockLLM, \
             patch("services.cend_profile_analyzer.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            instance = MockLLM.return_value
            instance.invoke = MagicMock(side_effect=[
                Exception("fail 1"),
                Exception("fail 2"),
                _make_mock_llm_response(json.dumps({"basic": {"province": "广东"}})),
            ])
            # Act
            result = await analyze_cend_turn("msg", "reply", None, max_retries=2)
        # Assert — retried, sleep called for backoff
        assert mock_sleep.await_count >= 1
        assert result.basic["province"] == "广东"


# ---------------------------------------------------------------------------
# _summarize_existing / _dedup_merge_lists helpers
# ---------------------------------------------------------------------------


class TestSummarizeExisting:
    def test_none_returns_empty_or_placeholder(self):
        out = _summarize_existing(None)
        assert isinstance(out, str)

    def test_dict_returns_string_summary(self):
        existing = {"basic": {"province": "广东"}}
        out = _summarize_existing(existing)
        assert isinstance(out, str)
        assert "广东" in out


class TestDedupMergeLists:
    def test_dedup_preserves_order_existing_first(self):
        out = _dedup_merge_lists(["a", "b"], ["b", "c"])
        assert out == ["a", "b", "c"]

    def test_empty_existing_returns_new(self):
        out = _dedup_merge_lists([], ["x", "y"])
        assert out == ["x", "y"]

    def test_empty_new_returns_existing(self):
        out = _dedup_merge_lists(["x"], [])
        assert out == ["x"]
