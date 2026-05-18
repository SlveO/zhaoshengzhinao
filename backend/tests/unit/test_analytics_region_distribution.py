import pytest
from analytics.region_distribution import get_region_distribution


@pytest.mark.asyncio
async def test_region_distribution_returns_empty_when_no_data():
    result = await get_region_distribution("00000000-0000-0000-0000-000000000000", days=1)
    assert result["regions"] == []


@pytest.mark.asyncio
async def test_region_distribution_items_have_required_fields():
    result = await get_region_distribution("00000000-0000-0000-0000-000000000000", days=365)
    for item in result["regions"]:
        assert "province" in item
        assert "city" in item
        assert "studentCount" in item
        assert "avgScore" in item
