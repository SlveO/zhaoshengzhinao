import pytest
from analytics.funnel import get_funnel


@pytest.mark.asyncio
async def test_funnel_returns_empty_when_no_events():
    result = await get_funnel("00000000-0000-0000-0000-000000000000", days=1)
    assert result["stages"]["visitors"] == 0
    assert result["stages"]["conversations"] == 0


@pytest.mark.asyncio
async def test_funnel_has_all_five_stages():
    result = await get_funnel("00000000-0000-0000-0000-000000000000", days=1)
    assert set(result["stages"].keys()) == {
        "visitors", "conversations", "deepConsultations", "intentExpressed", "enrolled"
    }


@pytest.mark.asyncio
async def test_funnel_has_period():
    result = await get_funnel("00000000-0000-0000-0000-000000000000", days=1)
    assert "period" in result
    assert "start" in result["period"]
    assert "end" in result["period"]


@pytest.mark.asyncio
async def test_funnel_conversion_rates_in_valid_range():
    result = await get_funnel("00000000-0000-0000-0000-000000000000", days=1)
    for rate in result["conversionRates"].values():
        assert 0 <= rate <= 100


@pytest.mark.asyncio
async def test_funnel_conversion_rates_keys():
    result = await get_funnel("00000000-0000-0000-0000-000000000000", days=1)
    assert set(result["conversionRates"].keys()) == {
        "visitorToConversation", "conversationToDeep",
        "deepToIntent", "intentToEnrolled",
    }
