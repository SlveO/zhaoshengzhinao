import pytest
from analytics.major_heatmap import get_major_heatmap
from tests.conftest import TEST_TENANT_ID


@pytest.mark.asyncio
async def test_major_heatmap_returns_empty_when_no_events():
    result = await get_major_heatmap("00000000-0000-0000-0000-000000000000", days=1)
    assert result["majors"] == []


@pytest.mark.asyncio
async def test_major_heatmap_items_have_required_fields():
    result = await get_major_heatmap("00000000-0000-0000-0000-000000000000", days=365)
    for item in result["majors"]:
        assert "majorName" in item
        assert "consultationCount" in item
        assert "recommendationCount" in item
        assert "intentCount" in item
        assert "heatScore" in item


@pytest.mark.asyncio
async def test_major_heatmap_sorted_by_heat_score():
    result = await get_major_heatmap("00000000-0000-0000-0000-000000000000", days=365)
    scores = [m["heatScore"] for m in result["majors"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_major_heatmap_aggregates_seeded_events(test_tenant, seed_event):
    session_id = "66666666-6666-6666-6666-666666666666"
    await seed_event("recommendation.feedback", session_id=session_id, payload={"major_name": "计算机科学与技术"})
    await seed_event("recommendation.feedback", session_id=session_id, payload={"major_name": "计算机科学与技术"})
    await seed_event("page.intent_expressed", session_id=session_id, payload={"majors_of_interest": ["计算机科学与技术", "软件工程"]})
    await seed_event("recommendation.generated", session_id=session_id, payload={"major_name": "计算机科学与技术"})

    result = await get_major_heatmap(str(TEST_TENANT_ID), days=7)

    top = result["majors"][0]
    assert top["majorName"] == "计算机科学与技术"
    assert top["recommendationCount"] == 2
    assert top["intentCount"] == 1
    assert top["consultationCount"] == 1
