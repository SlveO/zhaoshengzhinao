import pytest
from analytics.region_distribution import get_region_distribution
from tests.conftest import TEST_TENANT_ID


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


@pytest.mark.asyncio
async def test_region_distribution_aggregates_seeded_profiles(test_tenant, seed_session_profile):
    await seed_session_profile(profile_json={"region_pref": ["广东"], "score": 610})
    await seed_session_profile(profile_json={"region_pref": ["广东", "广西"], "score": 590})

    result = await get_region_distribution(str(TEST_TENANT_ID), days=7)

    regions = {item["province"]: item for item in result["regions"]}
    assert regions["广东"]["studentCount"] == 2
    assert regions["广东"]["avgScore"] == 600
    assert regions["广西"]["studentCount"] == 1
