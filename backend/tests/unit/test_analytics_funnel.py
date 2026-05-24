import pytest
from analytics.funnel import get_funnel
from tests.conftest import TEST_TENANT_ID


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


@pytest.mark.asyncio
async def test_funnel_aggregates_seeded_events(test_tenant, seed_event):
    user_id = "55555555-5555-5555-5555-555555555555"
    session_id = "66666666-6666-6666-6666-666666666666"

    await seed_event("page.viewed", user_id=user_id, session_id=session_id)
    await seed_event("chat.message_sent", user_id=user_id, session_id=session_id, payload={"turn": 1})
    await seed_event(
        "profile.updated",
        user_id=user_id,
        session_id=session_id,
        payload={"completeness": "L2"},
    )
    await seed_event("page.intent_expressed", user_id=user_id, session_id=session_id)

    result = await get_funnel(str(TEST_TENANT_ID), days=7)

    assert result["stages"]["visitors"] == 1
    assert result["stages"]["conversations"] == 1
    assert result["stages"]["deepConsultations"] == 1
    assert result["stages"]["intentExpressed"] == 1
    assert result["conversionRates"]["visitorToConversation"] == 100
