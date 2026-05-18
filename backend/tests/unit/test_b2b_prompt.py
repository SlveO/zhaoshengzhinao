"""Verify B2B prompt uses university-specific context, not generic advisor role."""
from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT, B2B_FEW_SHOT_EXAMPLES


def test_prompt_contains_university_name_placeholder():
    assert "{university_name}" in B2B_SYSTEM_PROMPT
    assert "{university_short}" in B2B_SYSTEM_PROMPT


def test_prompt_formatted_with_scnu():
    result = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华南师大",
        stage="open",
        slots_summary="暂无信息",
    )
    assert "华南师范大学" in result
    assert "华南师大" in result
    assert "open" in result


def test_prompt_does_not_contain_old_generic_role():
    """The B2B prompt should NOT use the old '高考志愿填报心理咨询师' role."""
    result = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华南师大",
        stage="open",
        slots_summary="暂无信息",
    )
    assert "心理咨询师" not in result
    assert "招生顾问" in result


def test_prompt_has_b2b_focus():
    """B2B prompt should focus on the specific university's programs."""
    result = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华南师大",
        stage="explore",
        slots_summary="学生喜欢动手操作",
    )
    assert "聚焦本校" in result
    assert "华南师范大学" in result


def test_few_shot_examples_exist():
    assert len(B2B_FEW_SHOT_EXAMPLES) >= 6


def test_few_shot_examples_are_b2b_focused():
    """B2B examples should include university-specific scenarios."""
    types = [e["type"] for e in B2B_FEW_SHOT_EXAMPLES]
    assert "师范型" in types  # SCNU is a normal university
    assert "好奇型" in types  # students asking about the university
