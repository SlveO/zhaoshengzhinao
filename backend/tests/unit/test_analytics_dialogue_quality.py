import pytest
from analytics.dialogue_quality import get_dialogue_quality


@pytest.mark.asyncio
async def test_dialogue_quality_structure():
    result = await get_dialogue_quality("00000000-0000-0000-0000-000000000000", days=1)
    assert "metrics" in result
    metrics = result["metrics"]
    assert "avgTurnsPerSession" in metrics
    assert "completionRate" in metrics
    assert "avgSatisfaction" in metrics
    assert "topQuestions" in metrics


@pytest.mark.asyncio
async def test_dialogue_quality_metrics_in_valid_range():
    result = await get_dialogue_quality("00000000-0000-0000-0000-000000000000", days=1)
    m = result["metrics"]
    assert 0 <= m["avgTurnsPerSession"] <= 1000
    assert 0 <= m["completionRate"] <= 100
    assert 0 <= m["avgSatisfaction"] <= 100


@pytest.mark.asyncio
async def test_dialogue_quality_top_questions_structure():
    result = await get_dialogue_quality("00000000-0000-0000-0000-000000000000", days=1)
    for item in result["metrics"]["topQuestions"]:
        assert "question" in item
        assert "count" in item
