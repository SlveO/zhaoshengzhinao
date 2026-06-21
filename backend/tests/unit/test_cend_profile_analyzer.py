"""Unit tests for cend_profile_analyzer — pure logic, no I/O, no DB.

Test names follow the required naming convention:
test_<method>_<scenario>_<expected_result>
"""

import os

# Prevent numpy BLAS FPE crash on Windows when langchain_openai imports torch
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import pytest

from services.cend_profile_analyzer import (
    CendExtractionResult,
    parse_cend_response,
    merge_extraction_results,
    _compute_completeness,
    _summarize_existing,
    build_cend_analysis_prompt,
    _dedup_merge_lists,
    RIASEC_KEYS,
)


# ---------------------------------------------------------------------------
# Override conftest.py's autouse setup_db fixture — NO database needed
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_db():
    """Override the conftest.py setup_db — pure unit tests, no DB required."""
    yield


# ===========================================================================
# 1. parse_cend_response
# ===========================================================================


def test_parse_cend_response_valid_json_returns_result():
    """Valid JSON populates all fields in CendExtractionResult."""
    # Arrange
    raw = (
        '{"basic":{"province":"广东","subject_type":"物理类","score":600},'
        '"interests":{"preferred_subjects":["数学","物理"],"strong_subjects":["物理"],"hobbies":["编程"]},'
        '"concerns":["担心考不上"],'
        '"riasec":{"R":7,"I":8,"A":5,"S":6,"E":4,"C":3},'
        '"values":["个人成长","薪资水平"],'
        '"region_pref":{"province":"广东","city":"广州"},'
        '"extra":{"key":"val"}}'
    )

    # Act
    result = parse_cend_response(raw)

    # Assert
    assert result.basic["province"] == "广东"
    assert result.basic["subject_type"] == "物理类"
    assert result.basic["score"] == 600
    assert result.interests["preferred_subjects"] == ["数学", "物理"]
    assert result.interests["strong_subjects"] == ["物理"]
    assert result.interests["hobbies"] == ["编程"]
    assert result.concerns == ["担心考不上"]
    assert result.riasec["R"] == 7
    assert result.riasec["I"] == 8
    assert result.riasec["A"] == 5
    assert result.riasec["S"] == 6
    assert result.riasec["E"] == 4
    assert result.riasec["C"] == 3
    assert result.values == ["个人成长", "薪资水平"]
    assert result.region_pref["province"] == "广东"
    assert result.region_pref["city"] == "广州"
    assert result.extra == {"key": "val"}
    assert result.has_any_data() is True


def test_parse_cend_response_markdown_wrapped_returns_result():
    """Markdown ```json...``` code block is stripped and parsed correctly."""
    # Arrange
    raw = (
        '```json\n'
        '{"basic":{"province":"北京"},"riasec":{"R":5,"I":6,"A":0,"S":0,"E":0,"C":0}}\n'
        '```'
    )

    # Act
    result = parse_cend_response(raw)

    # Assert
    assert result.basic["province"] == "北京"
    assert result.riasec["R"] == 5
    assert result.riasec["I"] == 6


def test_parse_cend_response_empty_string_returns_default():
    """Empty string returns default CendExtractionResult with no data."""
    # Arrange & Act
    result = parse_cend_response("")

    # Assert
    assert result.has_any_data() is False
    assert result.completeness == "L1"
    assert result.basic["province"] is None
    assert result.basic["score"] is None


def test_parse_cend_response_invalid_json_returns_default():
    """Garbage text that is not JSON returns default result."""
    # Arrange & Act
    result = parse_cend_response("not valid json at all !@#$%")

    # Assert
    assert result.has_any_data() is False
    assert result.completeness == "L1"


def test_parse_cend_response_none_returns_default():
    """None input returns default result (robustness)."""
    # Arrange & Act
    result = parse_cend_response(None)

    # Assert
    assert result.has_any_data() is False


def test_parse_cend_response_non_dict_json_returns_default():
    """JSON list/array (not dict) returns default result."""
    # Arrange & Act
    result = parse_cend_response('[1, 2, 3]')

    # Assert
    assert result.has_any_data() is False


def test_parse_cend_response_string_score_converted_to_int():
    """Score provided as string digit is converted to int."""
    # Arrange
    raw = '{"basic":{"score":"600"}}'

    # Act
    result = parse_cend_response(raw)

    # Assert
    assert result.basic["score"] == 600
    assert isinstance(result.basic["score"], int)


def test_parse_cend_response_invalid_riasec_values_ignored():
    """RIASEC values outside 1-10 are ignored (stay 0)."""
    # Arrange
    raw = '{"riasec":{"R":15,"I":-1,"A":"abc","S":0}}'

    # Act
    result = parse_cend_response(raw)

    # Assert
    assert result.riasec["R"] == 0  # 15 > 10, ignored
    assert result.riasec["I"] == 0  # -1, ignored
    assert result.riasec["A"] == 0  # "abc", not int
    assert result.riasec["S"] == 0  # 0 = not mentioned


def test_parse_cend_response_markdown_no_lang_tag_returns_result():
    """Markdown ```...``` without json tag is also stripped."""
    # Arrange
    raw = '```\n{"basic":{"province":"上海"},"riasec":{"R":0,"I":0,"A":0,"S":0,"E":0,"C":0}}\n```'

    # Act
    result = parse_cend_response(raw)

    # Assert
    assert result.basic["province"] == "上海"


def test_parse_cend_response_partial_json_fills_defaults():
    """Partial JSON fills only the provided fields; others stay default."""
    # Arrange
    raw = '{"basic":{"province":"广东"}}'

    # Act
    result = parse_cend_response(raw)

    # Assert
    assert result.basic["province"] == "广东"
    assert result.basic["score"] is None
    assert result.basic["subject_type"] is None
    assert result.has_any_data() is True


# ===========================================================================
# 2. _compute_completeness
# ===========================================================================


def test_completeness_l3_with_4_riasec_and_values():
    """>=4 RIASEC dims non-zero AND values non-empty -> L3."""
    # Arrange
    r = CendExtractionResult()
    r.riasec = {"R": 7, "I": 8, "A": 5, "S": 6, "E": 0, "C": 0}
    r.values = ["个人成长"]

    # Act
    level = _compute_completeness(r)

    # Assert
    assert level == "L3"


def test_completeness_l2_with_2_riasec_and_region():
    """>=2 RIASEC dims non-zero AND region_pref has data -> L2."""
    # Arrange
    r = CendExtractionResult()
    r.riasec = {"R": 7, "I": 8, "A": 0, "S": 0, "E": 0, "C": 0}
    r.region_pref = {"province": "广东", "city": None}

    # Act
    level = _compute_completeness(r)

    # Assert
    assert level == "L2"


def test_completeness_l1_default():
    """Empty/new result -> L1."""
    # Arrange
    r = CendExtractionResult()

    # Act
    level = _compute_completeness(r)

    # Assert
    assert level == "L1"


def test_completeness_l2_with_city_only_region():
    """Region with only city (no province) still counts as region data -> L2."""
    # Arrange
    r = CendExtractionResult()
    r.riasec = {"R": 7, "I": 0, "A": 8, "S": 0, "E": 0, "C": 0}
    r.region_pref = {"province": None, "city": "广州"}

    # Act
    level = _compute_completeness(r)

    # Assert
    assert level == "L2"


def test_completeness_l1_with_3_riasec_no_values_or_region():
    """3 RIASEC dims but no values and no region -> stays L1 (not enough for L3/L2)."""
    # Arrange
    r = CendExtractionResult()
    r.riasec = {"R": 7, "I": 8, "A": 5, "S": 0, "E": 0, "C": 0}

    # Act
    level = _compute_completeness(r)

    # Assert
    assert level == "L1"


# ===========================================================================
# 3. merge_extraction_results
# ===========================================================================


def test_merge_basic_override_new_overrides_old():
    """New non-null basic fields override existing values."""
    # Arrange
    existing = CendExtractionResult()
    existing.basic["province"] = "广东"
    existing.basic["score"] = 550

    new_ext = CendExtractionResult()
    new_ext.basic["province"] = "北京"
    new_ext.basic["score"] = 600

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    assert merged.basic["province"] == "北京"
    assert merged.basic["score"] == 600


def test_merge_basic_new_none_keeps_old():
    """When new field is None, old value is preserved."""
    # Arrange
    existing = CendExtractionResult()
    existing.basic["province"] = "广东"

    new_ext = CendExtractionResult()
    # province stays None (default)

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    assert merged.basic["province"] == "广东"


def test_merge_list_dedup_combines_unique():
    """preferred_subjects from both results are merged with deduplication."""
    # Arrange
    existing = CendExtractionResult()
    existing.interests["preferred_subjects"] = ["数学", "物理"]

    new_ext = CendExtractionResult()
    new_ext.interests["preferred_subjects"] = ["物理", "计算机"]

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    assert merged.interests["preferred_subjects"] == ["数学", "物理", "计算机"]


def test_merge_riasec_nonzero_overrides_zero():
    """New RIASEC > 0 overrides existing RIASEC = 0 (not mentioned)."""
    # Arrange
    existing = CendExtractionResult()
    existing.riasec["R"] = 7
    existing.riasec["I"] = 5

    new_ext = CendExtractionResult()
    new_ext.riasec["R"] = 9  # override existing
    new_ext.riasec["A"] = 6  # new dimension
    new_ext.riasec["I"] = 0  # 0 = not mentioned, keep old

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    assert merged.riasec["R"] == 9
    assert merged.riasec["I"] == 5  # preserved from old
    assert merged.riasec["A"] == 6  # added from new


def test_merge_concerns_dedup_preserves_order():
    """Concerns list merged with dedup, existing items first."""
    # Arrange
    existing = CendExtractionResult()
    existing.concerns = ["担心考不上", "不知道选什么专业"]

    new_ext = CendExtractionResult()
    new_ext.concerns = ["不知道选什么专业", "怕滑档"]

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    assert merged.concerns == ["担心考不上", "不知道选什么专业", "怕滑档"]


def test_merge_values_dedup_combines():
    """Values from both results merged unique."""
    # Arrange
    existing = CendExtractionResult()
    existing.values = ["个人成长", "薪资水平"]

    new_ext = CendExtractionResult()
    new_ext.values = ["薪资水平", "社会贡献"]

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    assert merged.values == ["个人成长", "薪资水平", "社会贡献"]


def test_merge_region_pref_new_overrides_old():
    """Region_pref new non-null overrides old, null preserves old."""
    # Arrange
    existing = CendExtractionResult()
    existing.region_pref["province"] = "广东"
    existing.region_pref["city"] = "广州"

    new_ext = CendExtractionResult()
    new_ext.region_pref["province"] = "北京"
    # city stays None (default)

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    assert merged.region_pref["province"] == "北京"
    assert merged.region_pref["city"] == "广州"  # preserved from old


def test_merge_extra_shallow_new_keys_override():
    """Extra dict shallow-merged, new keys override old."""
    # Arrange
    existing = CendExtractionResult()
    existing.extra = {"a": 1, "b": 2}

    new_ext = CendExtractionResult()
    new_ext.extra = {"b": 99, "c": 3}

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    assert merged.extra == {"a": 1, "b": 99, "c": 3}


def test_merge_recomputes_completeness_after_merge():
    """Completeness is recomputed from merged result, not copied."""
    # Arrange
    existing = CendExtractionResult()
    existing.riasec = {"R": 7, "I": 8, "A": 0, "S": 0, "E": 0, "C": 0}
    existing.region_pref = {"province": "广东", "city": None}
    existing.completeness = "L2"

    new_ext = CendExtractionResult()
    new_ext.riasec = {"A": 5, "S": 6}  # adds 2 more RIASEC dims
    new_ext.values = ["个人成长"]       # adds values

    # Act
    merged = merge_extraction_results(existing, new_ext)

    # Assert
    # After merge: R=7, I=8, A=5, S=6 = 4 dims + values -> L3
    assert merged.completeness == "L3"


# ===========================================================================
# 4. _summarize_existing
# ===========================================================================


def test_summarize_existing_none_profile_returns_placeholder():
    """None profile returns placeholder text."""
    # Act
    summary = _summarize_existing(None)

    # Assert
    assert "暂无" in summary


def test_summarize_existing_empty_profile_returns_placeholder():
    """Empty dict returns placeholder text."""
    # Act
    summary = _summarize_existing({})

    # Assert
    assert "暂无" in summary


def test_summarize_existing_full_profile_includes_all_sections():
    """Full profile dict produces summary containing all section data."""
    # Arrange
    profile = {
        "basic": {"province": "广东", "subject_type": "物理类", "score": 600},
        "interests": {"preferred_subjects": ["数学", "物理"]},
        "riasec": {"R": 7, "I": 8},
        "values": ["个人成长"],
        "concerns": ["担心考不上"],
        "region_pref": {"province": "广东", "city": "广州"},
    }

    # Act
    summary = _summarize_existing(profile)

    # Assert
    assert "广东" in summary
    assert "物理类" in summary
    assert "600" in summary
    assert "个人成长" in summary
    assert "担心考不上" in summary
    assert "广州" in summary


# ===========================================================================
# 5. build_cend_analysis_prompt
# ===========================================================================


def test_build_prompt_includes_existing_profile():
    """Prompt contains summarized existing profile data (not raw placeholder)."""
    # Arrange
    profile = {"basic": {"province": "广东", "score": 600}}

    # Act
    prompt = build_cend_analysis_prompt("我想学计算机", "计算机前景很好", profile)

    # Assert
    assert "广东" in prompt
    assert "600" in prompt
    assert "existing_profile_summary" not in prompt  # placeholder is replaced
    assert "我想学计算机" in prompt
    assert "计算机前景很好" in prompt


def test_build_prompt_no_existing_profile_shows_placeholder():
    """When no existing profile, prompt shows the placeholder text."""
    # Act
    prompt = build_cend_analysis_prompt("你好", "你好，有什么可以帮你的？", None)

    # Assert
    assert "暂无已有画像数据" in prompt
    assert "你好" in prompt
    assert "existing_profile_summary" not in prompt


# ===========================================================================
# 6. _dedup_merge_lists
# ===========================================================================


def test_dedup_merge_lists_preserves_order_existing_first():
    """Existing items first, then new unique items, preserving relative order."""
    # Act
    result = _dedup_merge_lists(["a", "b", "c"], ["b", "d", "a"])

    # Assert
    assert result == ["a", "b", "c", "d"]


def test_dedup_merge_lists_empty_new_unchanged():
    """When new list is empty, existing list is returned unchanged."""
    # Act
    result = _dedup_merge_lists(["x", "y"], [])

    # Assert
    assert result == ["x", "y"]


def test_dedup_merge_lists_empty_existing_returns_new():
    """When existing list is empty, new list is returned."""
    # Act
    result = _dedup_merge_lists([], ["a", "b"])

    # Assert
    assert result == ["a", "b"]


# ===========================================================================
# 7. CendExtractionResult dataclass
# ===========================================================================


def test_cend_extraction_result_default_is_empty():
    """Default constructed result has no data and L1 completeness."""
    # Act
    r = CendExtractionResult()

    # Assert
    assert r.completeness == "L1"
    assert r.has_any_data() is False


def test_cend_extraction_result_to_profile_json_includes_all_keys():
    """to_profile_json returns all expected top-level keys."""
    # Arrange
    r = CendExtractionResult()

    # Act
    j = r.to_profile_json()

    # Assert
    for key in ("basic", "interests", "concerns", "riasec", "values", "region_pref", "extra", "completeness"):
        assert key in j


def test_cend_extraction_result_has_any_data_with_province():
    """has_any_data returns True when basic.province is set."""
    # Arrange
    r = CendExtractionResult()
    r.basic["province"] = "广东"

    # Assert
    assert r.has_any_data() is True


def test_cend_extraction_result_has_any_data_with_riasec():
    """has_any_data returns True when any RIASEC dim > 0."""
    # Arrange
    r = CendExtractionResult()
    r.riasec["R"] = 7

    # Assert
    assert r.has_any_data() is True


def test_cend_extraction_result_has_any_data_with_concerns():
    """has_any_data returns True when concerns list is non-empty."""
    # Arrange
    r = CendExtractionResult()
    r.concerns = ["担心"]

    # Assert
    assert r.has_any_data() is True


def test_cend_extraction_result_has_any_data_with_region():
    """has_any_data returns True when region_pref has data."""
    # Arrange
    r = CendExtractionResult()
    r.region_pref["city"] = "广州"

    # Assert
    assert r.has_any_data() is True


def test_cend_extraction_result_has_any_data_with_extra():
    """has_any_data returns True when extra dict is non-empty."""
    # Arrange
    r = CendExtractionResult()
    r.extra = {"key": "value"}

    # Assert
    assert r.has_any_data() is True
