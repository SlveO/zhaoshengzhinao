import pytest
from analytics.competitive_analysis import get_competitive_analysis
from tests.conftest import TEST_TENANT_ID


@pytest.mark.asyncio
async def test_competitive_analysis_structure():
    result = await get_competitive_analysis("00000000-0000-0000-0000-000000000000", days=1)
    assert "comparisonDimensions" in result
    assert "lossAnalysis" in result
    assert isinstance(result["comparisonDimensions"], list)
    assert isinstance(result["lossAnalysis"], list)


@pytest.mark.asyncio
async def test_comparison_dimensions_have_required_fields():
    result = await get_competitive_analysis("00000000-0000-0000-0000-000000000000", days=365)
    for item in result["comparisonDimensions"]:
        assert "dimension" in item
        assert "ourScore" in item
        assert "competitorAvgScore" in item


@pytest.mark.asyncio
async def test_loss_analysis_have_required_fields():
    result = await get_competitive_analysis("00000000-0000-0000-0000-000000000000", days=365)
    for item in result["lossAnalysis"]:
        assert "reason" in item
        assert "percentage" in item
        assert 0 <= item["percentage"] <= 100


@pytest.mark.asyncio
async def test_competitive_analysis_aggregates_seeded_data(test_tenant, seed_session_profile, seed_event):
    await seed_session_profile(profile_json={"riasec": {"R": 8, "I": 6}})
    await seed_event("recommendation.feedback", payload={"feedback": "地域偏好不匹配"})
    await seed_event("recommendation.feedback", payload={"feedback": "分数线不匹配"})

    result = await get_competitive_analysis(str(TEST_TENANT_ID), days=7)

    dims = {item["dimension"]: item["ourScore"] for item in result["comparisonDimensions"]}
    assert dims["动手操作"] == 8.0
    reasons = {item["reason"]: item["percentage"] for item in result["lossAnalysis"]}
    assert reasons["地域偏好不匹配"] == 50.0
