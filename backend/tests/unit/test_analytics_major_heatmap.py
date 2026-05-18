import pytest
from analytics.major_heatmap import get_major_heatmap


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
