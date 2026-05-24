import pytest
from analytics.profile_dashboard import get_profile_dashboard
from tests.conftest import TEST_TENANT_ID


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


@pytest.mark.asyncio
async def test_profile_dashboard_aggregates_seeded_profiles(test_tenant, seed_session_profile):
    await seed_session_profile(
        profile_json={
            "riasec": {"R": 8, "I": 6},
            "values": ["稳定", "成长"],
            "region_pref": ["广东"],
            "score": 610,
        },
        completeness="L2",
    )
    await seed_session_profile(
        profile_json={
            "riasec": {"R": 4, "S": 7},
            "values": ["稳定"],
            "region_pref": ["广西"],
            "score": 580,
        },
        completeness="L3",
    )

    result = await get_profile_dashboard(str(TEST_TENANT_ID), days=7)

    assert result["totalProfiles"] == 2
    riasec = {item["dimension"]: item for item in result["riasecDistribution"]}
    assert riasec["R"]["avgScore"] == 6.0
    values = {item["value"]: item["percentage"] for item in result["valuesDistribution"]}
    assert values["稳定"] == pytest.approx(66.7)
    completeness = {item["level"]: item["count"] for item in result["completenessBreakdown"]}
    assert completeness == {"L2": 1, "L3": 1}
