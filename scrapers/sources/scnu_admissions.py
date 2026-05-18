"""SCNU admission scores scraper — multi-province via gaokao.cn API.

Target: 华南师范大学 (MOE 10574, platform_id 98)
Coverage: 2021-2025, 10 provinces
"""
import asyncio
import httpx
from loguru import logger

from scrapers.config import ScraperConfig
from scrapers.base_scraper import BaseScraper

SCNU_PLATFORM_ID = 98
SCNU_MOE_CODE = "10574"
SCNU_NAME = "华南师范大学"

TARGET_YEARS = [2021, 2022, 2023, 2024, 2025]

PROVINCE_IDS: dict[int, str] = {
    44: "广东",
    11: "北京",
    31: "上海",
    32: "江苏",
    33: "浙江",
    42: "湖北",
    43: "湖南",
    51: "四川",
    37: "山东",
    41: "河南",
}


class SCNUAdmissionsScraper(BaseScraper):

    def __init__(self):
        super().__init__(ScraperConfig(
            name="scnu",
            base_url="https://static-data.gaokao.cn",
            delay_seconds=0.5,
        ))

    async def fetch_scores(
        self, client: httpx.AsyncClient, year: int, province_id: int
    ) -> list[dict]:
        url = (
            f"{self.config.base_url}/www/2.0/"
            f"schoolspecialscore/{SCNU_PLATFORM_ID}/{year}/{province_id}.json"
        )
        try:
            resp = await self.fetch_with_retry(client, url)
            return self._parse_score_response(resp, year, province_id)
        except Exception as e:
            logger.warning(
                f"Score fetch failed for SCNU {year}/p{province_id}: {e}"
            )
            return []

    def _parse_score_response(
        self, data: dict, year: int, province_id: int
    ) -> list[dict]:
        results = []
        province_name = PROVINCE_IDS.get(province_id, str(province_id))
        batches = data.get("data", {})
        if not isinstance(batches, dict):
            return results

        for _batch_key, batch_data in batches.items():
            if not isinstance(batch_data, dict):
                continue
            items = batch_data.get("item", [])
            for item in items:
                results.append({
                    "college_code": SCNU_MOE_CODE,
                    "college_name": SCNU_NAME,
                    "major_name": item.get("sp_name", ""),
                    "major_group": item.get("sg_name", ""),
                    "year": year,
                    "province": province_name,
                    "province_id": province_id,
                    "batch": item.get("local_batch_name", "本科批"),
                    "subject_requirements": item.get("sg_info", ""),
                    "plan_count": self._parse_int(item.get("lq_num")),
                    "min_score": self._parse_int(item.get("min")),
                    "min_rank": self._parse_int(item.get("min_section")),
                    "avg_score": self._parse_int(item.get("average")),
                    "max_score": self._parse_int(item.get("max")),
                    "source_url": (
                        f"https://static-data.gaokao.cn/www/2.0/"
                        f"schoolspecialscore/{SCNU_PLATFORM_ID}"
                        f"/{year}/{province_id}.json"
                    ),
                })
        return results

    @staticmethod
    def _parse_int(val) -> int | None:
        if val is None or val == "-" or val == "":
            return None
        try:
            return int(str(val).replace(",", "").strip())
        except (ValueError, TypeError):
            return None

    async def run(self) -> dict:
        all_scores = []
        errors = []

        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            headers=self.config.headers,
            limits=httpx.Limits(max_connections=8),
        ) as client:
            sem = asyncio.Semaphore(6)

            async def fetch_one(year: int, province_id: int):
                async with sem:
                    return await self.fetch_scores(client, year, province_id)

            tasks = []
            for year in TARGET_YEARS:
                for pid in PROVINCE_IDS:
                    tasks.append((year, pid))

            logger.info(
                f"Fetching SCNU admissions: {len(TARGET_YEARS)} years x "
                f"{len(PROVINCE_IDS)} provinces = {len(tasks)} requests"
            )

            results = await asyncio.gather(*[fetch_one(y, p) for y, p in tasks])

            for (year, pid), batch in zip(tasks, results):
                if not batch:
                    errors.append({
                        "type": "admissions_empty",
                        "year": year,
                        "province_id": pid,
                        "province": PROVINCE_IDS.get(pid, str(pid)),
                    })
                all_scores.extend(batch)

            logger.info(
                f"SCNU admissions: {len(all_scores)} records, "
                f"{len(errors)} empty provinces"
            )

            self.save_raw("admissions.json", all_scores)
            if errors:
                self.save_raw("errors_admissions.json", errors)

        return {
            "source": "scnu_admissions",
            "records": len(all_scores),
            "errors": len(errors),
        }


if __name__ == "__main__":
    asyncio.run(SCNUAdmissionsScraper().run())
