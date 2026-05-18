import pytest
from analytics.competitive_analysis import get_competitive_analysis


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
