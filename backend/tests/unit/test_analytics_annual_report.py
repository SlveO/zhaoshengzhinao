import pytest
from analytics.annual_report import get_annual_report


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
