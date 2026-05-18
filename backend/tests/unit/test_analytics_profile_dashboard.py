import pytest
from analytics.profile_dashboard import get_profile_dashboard


@pytest.mark.asyncio
async def test_profile_dashboard_returns_empty_when_no_profiles():
    result = await get_profile_dashboard("00000000-0000-0000-0000-000000000000", days=1)
    assert result["totalProfiles"] == 0
    assert isinstance(result["riasecDistribution"], list)
    assert isinstance(result["valuesDistribution"], list)
    assert isinstance(result["completenessBreakdown"], list)


@pytest.mark.asyncio
async def test_profile_dashboard_structure():
    result = await get_profile_dashboard("00000000-0000-0000-0000-000000000000", days=1)
    assert set(result.keys()) == {
        "riasecDistribution", "valuesDistribution",
        "completenessBreakdown", "totalProfiles",
    }


@pytest.mark.asyncio
async def test_riasec_distribution_items_have_required_fields():
    result = await get_profile_dashboard("00000000-0000-0000-0000-000000000000", days=365)
    for item in result["riasecDistribution"]:
        assert "dimension" in item
        assert "avgScore" in item
        assert "count" in item


@pytest.mark.asyncio
async def test_values_distribution_items_have_required_fields():
    result = await get_profile_dashboard("00000000-0000-0000-0000-000000000000", days=1)
    for item in result["valuesDistribution"]:
        assert "value" in item
        assert "percentage" in item
