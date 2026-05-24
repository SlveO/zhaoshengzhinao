import pytest
from analytics.dialogue_quality import get_dialogue_quality
from tests.conftest import TEST_TENANT_ID


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


@pytest.mark.asyncio
async def test_dialogue_quality_aggregates_seeded_events(test_tenant, seed_event):
    session_id = "66666666-6666-6666-6666-666666666666"
    await seed_event("chat.message_sent", session_id=session_id, payload={"turn": 1, "stage": "open"})
    await seed_event("chat.message_sent", session_id=session_id, payload={"turn": 3, "stage": "focus"})
    await seed_event("chat.stage_changed", session_id=session_id, payload={"to_stage": "confirm"})
    await seed_event("recommendation.feedback", session_id=session_id, payload={"feedback": "useful"})

    result = await get_dialogue_quality(str(TEST_TENANT_ID), days=7)

    metrics = result["metrics"]
    assert metrics["avgTurnsPerSession"] == 3.0
    assert metrics["completionRate"] == 100.0
    assert metrics["avgSatisfaction"] == 100.0
    assert metrics["topQuestions"][0]["question"] in {"open", "focus"}
