"""Collect and parse university employment quality reports."""
import asyncio
from pathlib import Path
import httpx
from loguru import logger

from scrapers.config import (
    ScraperConfig, GUANGDONG_UNIVERSITIES, DATA_RAW,
)
from scrapers.base_scraper import BaseScraper
from scrapers.parsers.pdf_parser import (
    extract_text_from_pdf, parse_employment_rate,
    parse_avg_salary, parse_graduate_rates, parse_industry_distribution,
)
from scrapers.storage.schema import Employment


# Known employment report URLs for major Guangdong universities
KNOWN_REPORT_URLS: dict[str, str] = {
    "10558": "https://jyzd.sysu.edu.cn/report/2024.pdf",
    "10561": "https://jyzd.scut.edu.cn/report/2024.pdf",
    "10559": "https://jyzd.jnu.edu.cn/report/2024.pdf",
    "10574": "https://career.scnu.edu.cn/report/2024.pdf",
    "10590": "https://career.szu.edu.cn/report/2024.pdf",
    "11845": "https://jyzd.gdut.edu.cn/report/2024.pdf",
}


class UniversityReportScraper(BaseScraper):
    """Downloads and parses university employment quality reports."""

    def __init__(self):
        super().__init__(ScraperConfig(
            name="university_reports",
            base_url="",
            delay_seconds=3.0,
        ))
        self.pdf_dir = DATA_RAW / "employment_pdfs"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    async def download_pdf(
        self, client: httpx.AsyncClient, url: str, filename: str
    ) -> Path | None:
        """Download PDF and save to disk."""
        path = self.pdf_dir / filename
        if path.exists():
            logger.info(f"PDF already downloaded: {path}")
            return path
        try:
            resp = await client.get(url, timeout=60)
            resp.raise_for_status()
            path.write_bytes(resp.content)
            logger.info(f"Downloaded PDF: {path}")
            return path
        except Exception as e:
            logger.warning(f"Failed to download {url}: {e}")
            return None

    async def process_report(
        self, client: httpx.AsyncClient, code: str, name: str, year: int
    ) -> Employment | None:
        """Download and parse one school's employment report for one year."""
        url = KNOWN_REPORT_URLS.get(code)
        if not url:
            return None

        filename = f"{code}_{name}_{year}.pdf"
        pdf_path = await self.download_pdf(client, url, filename)
        if not pdf_path:
            return None

        text = extract_text_from_pdf(pdf_path)
        if not text:
            logger.warning(f"No text extracted from {pdf_path}")
            return None

        emp_rate = parse_employment_rate(text)
        salary = parse_avg_salary(text)
        grad_rates = parse_graduate_rates(text)
        industries = parse_industry_distribution(text)

        return Employment(
            college_code=code,
            major_name="全部专业",  # school-level aggregate
            year=year,
            employment_rate=emp_rate,
            avg_monthly_salary=salary,
            domestic_graduate_rate=grad_rates.get("domestic_graduate_rate"),
            overseas_rate=grad_rates.get("overseas_rate"),
            direct_employment_rate=(
                (emp_rate -
                 grad_rates.get("domestic_graduate_rate", 0) -
                 grad_rates.get("overseas_rate", 0))
                if emp_rate else None
            ),
            top_industries=industries,
            source=f"《{name}{year}届毕业生就业质量年度报告》",
        )

    async def run(self) -> dict:
        """Download and parse employment reports for all universities."""
        results: list[Employment] = []
        async with httpx.AsyncClient(timeout=60) as client:
            for year in [2023, 2024]:
                for uni in GUANGDONG_UNIVERSITIES:
                    emp = await self.process_report(
                        client, uni["code"], uni["name"], year
                    )
                    if emp:
                        results.append(emp)
                    await asyncio.sleep(1.0)

        self.save_raw(
            "employment.json",
            [e.model_dump() for e in results]
        )
        return {
            "source": "university_reports",
            "employment_records": len(results),
        }
