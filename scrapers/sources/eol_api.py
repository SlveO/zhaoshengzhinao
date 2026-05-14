"""掌上高考 (eol.cn) API scraper — primary source for admissions and majors."""
import asyncio
import httpx
from loguru import logger

from scrapers.config import (
    ScraperConfig, GUANGDONG_UNIVERSITIES, TARGET_YEARS, TARGET_PROVINCE,
)
from scrapers.base_scraper import BaseScraper


def _to_bool(val) -> bool:
    """Safely convert API value to bool. Handles '0'/'1' strings correctly."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip() in ("1", "true", "True", "是", "yes")
    if isinstance(val, (int, float)):
        return bool(int(val))
    return bool(val)


class EOLScraper(BaseScraper):
    """Scrapes 掌上高考 API for college, major, and admission score data."""

    def __init__(self):
        super().__init__(ScraperConfig(
            name="eol_api",
            base_url="https://api.eol.cn/gkcx/api",
            delay_seconds=1.0,
        ))

    async def fetch_college_detail(
        self, client: httpx.AsyncClient, code: str
    ) -> dict | None:
        """Fetch detailed info for one school by its code."""
        url = f"{self.config.base_url}/school/schoolDetailBySchoolCode"
        params = {
            "school_code": code,
            "uri": "apigkcx/api/school/querySchoolDetailBySchoolCode",
        }
        try:
            data = await self.fetch_with_retry(client, url, params)
            return data.get("data") if data else None
        except Exception as e:
            logger.warning(f"Failed to fetch college detail for {code}: {e}")
            return None

    async def fetch_colleges(self, client: httpx.AsyncClient) -> list[dict]:
        """Fetch all Guangdong university details."""
        results = []
        tasks = [self.fetch_college_detail(client, u["code"])
                 for u in GUANGDONG_UNIVERSITIES]
        details = await asyncio.gather(*tasks)
        for uni, detail in zip(GUANGDONG_UNIVERSITIES, details):
            if detail:
                results.append({**uni, **self._normalize_college(uni, detail)})
            else:
                results.append(dict(uni))
        logger.info(f"Fetched {len(results)} college records")
        self.save_raw("colleges.json", results)
        return results

    async def fetch_majors_for_school(
        self, client: httpx.AsyncClient, code: str
    ) -> list[dict]:
        """Fetch all majors for a school."""
        url = f"{self.config.base_url}/school/schoolSpe"
        params = {
            "school_id": code,
            "uri": "apigkcx/api/school/querySchoolSpe",
            "page": 1,
            "size": 500,
        }
        try:
            data = await self.fetch_with_retry(client, url, params)
            return data.get("data", {}).get("items", []) if data else []
        except Exception as e:
            logger.warning(f"Failed majors for {code}: {e}")
            return []

    async def fetch_all_majors(self, client: httpx.AsyncClient) -> list[dict]:
        """Fetch majors for all Guangdong universities."""
        all_majors = []
        for uni in GUANGDONG_UNIVERSITIES:
            majors = await self.fetch_majors_for_school(client, uni["code"])
            for m in majors:
                m["college_code"] = uni["code"]
            all_majors.extend(majors)
            await asyncio.sleep(0.3)
        logger.info(f"Fetched {len(all_majors)} major records")
        self.save_raw("majors.json", all_majors)
        return all_majors

    async def fetch_admission_scores(
        self, client: httpx.AsyncClient, school_code: str, year: int
    ) -> list[dict]:
        """Fetch admission scores for one school in one year, Guangdong province."""
        url = f"{self.config.base_url}/school/schoolAdmissionScore"
        params = {
            "school_id": school_code,
            "province": TARGET_PROVINCE,
            "year": str(year),
            "type": "理科,文科,综合",
            "uri": "apigkcx/api/school/querySchoolAdmissionScore",
        }
        try:
            data = await self.fetch_with_retry(client, url, params)
            return data.get("data", {}).get("items", []) if data else []
        except Exception as e:
            logger.warning(f"Failed scores for {school_code}/{year}: {e}")
            return []

    async def fetch_all_admissions(self, client: httpx.AsyncClient) -> list[dict]:
        """Fetch 6 years of admission scores for all 65 universities."""
        all_scores = []
        sem = asyncio.Semaphore(6)

        async def fetch_year(uni: dict, year: int):
            async with sem:
                scores = await self.fetch_admission_scores(client, uni["code"], year)
                for s in scores:
                    s["college_code"] = uni["code"]
                    s["year"] = year
                    s["province"] = TARGET_PROVINCE
                return scores

        tasks = []
        for uni in GUANGDONG_UNIVERSITIES:
            for year in TARGET_YEARS:
                tasks.append(fetch_year(uni, year))

        results = await asyncio.gather(*tasks)
        for batch in results:
            all_scores.extend(batch)

        logger.info(f"Fetched {len(all_scores)} admission records")
        self.save_raw("admissions.json", all_scores)
        return all_scores

    @staticmethod
    def _normalize_college(uni: dict, detail: dict) -> dict:
        """Merge API detail response into our schema fields."""
        return {
            "intro": detail.get("content",
                                 detail.get("school_introduce", "")),
            "website": detail.get("school_site",
                                   detail.get("site", "")),
            "student_count": detail.get("student_count"),
            "founded_year": detail.get("founding_year"),
            "ranking_soft_2024": detail.get("rank"),
            "is_985": _to_bool(detail.get("f985")),
            "is_211": _to_bool(detail.get("f211")),
            "is_double_first": _to_bool(detail.get("dual_class_name")),
        }

    async def run(self) -> dict:
        """Main entry: collect all data from eol.cn."""
        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            limits=httpx.Limits(max_connections=20),
        ) as client:
            logger.info("EOL: fetching colleges...")
            colleges = await self.fetch_colleges(client)

            logger.info("EOL: fetching majors...")
            raw_majors = await self.fetch_all_majors(client)

            logger.info(
                "EOL: fetching admission scores "
                f"({len(TARGET_YEARS)} years x {len(GUANGDONG_UNIVERSITIES)} schools)..."
            )
            raw_admissions = await self.fetch_all_admissions(client)

        return {
            "source": "eol_api",
            "colleges": len(colleges),
            "majors": len(raw_majors),
            "admissions": len(raw_admissions),
        }
