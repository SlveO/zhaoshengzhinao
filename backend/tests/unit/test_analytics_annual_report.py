import pytest
from analytics.annual_report import get_annual_report
from tests.conftest import TEST_TENANT_ID


@pytest.mark.asyncio
async def test_annual_report_structure():
    result = await get_annual_report("00000000-0000-0000-0000-000000000000", days=1)
    assert "report" in result
    report = result["report"]
    assert "year" in report
    assert "summary" in report
    assert "sections" in report
    assert isinstance(report["sections"], list)


@pytest.mark.asyncio
async def test_annual_report_sections_have_required_fields():
    result = await get_annual_report("00000000-0000-0000-0000-000000000000", days=1)
    for section in result["report"]["sections"]:
        assert "title" in section
        assert "content" in section
        assert "charts" in section


@pytest.mark.asyncio
async def test_annual_report_year_is_current():
    from datetime import datetime, timezone
    result = await get_annual_report("00000000-0000-0000-0000-000000000000", days=1)
    assert result["report"]["year"] == datetime.now(timezone.utc).year


@pytest.mark.asyncio
async def test_annual_report_reflects_seeded_summary(test_tenant, seed_event, seed_session_profile):
    await seed_event("page.viewed")
    await seed_event("chat.message_sent", payload={"turn": 1, "stage": "open"})
    await seed_event("recommendation.feedback", payload={"major_name": "计算机科学与技术", "feedback": "useful"})
    await seed_session_profile(profile_json={"riasec": {"I": 9}, "region_pref": ["广东"], "score": 610})

    result = await get_annual_report(str(TEST_TENANT_ID), days=7)

    summary = result["report"]["summary"]
    assert "累计服务 1 名潜在学生" in summary
    assert "完成 1 份学生画像" in summary
    assert len(result["report"]["sections"]) == 5
