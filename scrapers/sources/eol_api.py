"""掌上高考 / static-data.gaokao.cn API scraper — primary source for admission scores.

Uses the verified working endpoints:
  - static-data.gaokao.cn/www/2.0/school/{id}/info.json  (college info)
  - static-data.gaokao.cn/www/2.0/schoolspecialscore/{id}/{year}/44.json  (admission scores)
"""
import asyncio
import httpx
from loguru import logger

from scrapers.config import ScraperConfig, TARGET_YEARS, TARGET_PROVINCE
from scrapers.base_scraper import BaseScraper

# Mapping: MOE code (教育部代码) -> platform school_id on static-data.gaokao.cn
# Discovered from the /school/{id}/info.json endpoint
SCHOOL_ID_MAP: dict[str, int] = {
    "10558": 104,   # 中山大学
    "10561": 105,   # 华南理工大学
    "10559": 106,   # 暨南大学
    "10574": 98,    # 华南师范大学
    "10564": 287,   # 华南农业大学
    "12121": 960,   # 南方医科大学
    "10572": 289,   # 广州中医药大学
    "10590": 284,   # 深圳大学
    "11845": 286,   # 广东工业大学
    "11078": 293,   # 广州大学
    "11846": 290,   # 广东外语外贸大学
    "10560": 283,   # 汕头大学
    "14325": 0,     # 南方科技大学 — not on this platform
    "10570": 295,   # 广州医科大学
    "10592": 302,   # 广东财经大学
    "10566": 288,   # 广东海洋大学
    "11819": 291,   # 东莞理工学院
    "11847": 306,   # 佛山科学技术学院 (now 佛山大学)
    "11349": 285,   # 五邑大学
    "11347": 0,     # 仲恺农业工程学院 — need to find
    "10571": 294,   # 广东医科大学
    "10573": 296,   # 广东药科大学
    "10576": 298,   # 韶关学院
    "10577": 300,   # 惠州学院
    "10578": 297,   # 韩山师范学院
    "10579": 299,   # 岭南师范学院
    "10580": 961,   # 肇庆学院
    "10582": 301,   # 嘉应学院
    "10585": 303,   # 广州体育学院
    "10586": 304,   # 广州美术学院
    "10587": 305,   # 星海音乐学院
    "10588": 964,   # 广东技术师范大学
    "10591": 1031,  # 广东金融学院
    "11347": 0,     # 仲恺农业工程学院 — not found on platform
    "11540": 963,   # 广东警官学院
    "11819": 291,   # 东莞理工学院
    "11847": 306,   # 佛山科学技术学院 (佛山大学)
    "12059": 965,   # 广东培正学院
    "13667": 966,   # 广东白云学院
    "13902": 1096,  # 广州南方学院
    "14390": 967,   # 广州航海学院
    "16401": 0,     # 深圳技术大学 — not found
    "18272": 0,     # 香港中文大学(深圳) — not found
    "18398": 0,     # 香港科技大学(广州) — not found
}

PROVINCE_ID = 44  # 广东


class GaokaoScoreScraper(BaseScraper):
    """Fetches admission scores from static-data.gaokao.cn."""

    def __init__(self):
        super().__init__(ScraperConfig(
            name="gaokao_scores",
            base_url="https://static-data.gaokao.cn",
            delay_seconds=0.5,
        ))

    async def fetch_scores(
        self, client: httpx.AsyncClient, platform_id: int, year: int
    ) -> list[dict]:
        """Fetch all major-level admission scores for one school + year."""
        url = (
            f"{self.config.base_url}/www/2.0/"
            f"schoolspecialscore/{platform_id}/{year}/{PROVINCE_ID}.json"
        )
        try:
            resp = await self.fetch_with_retry(client, url)
            return self._parse_score_response(resp, year)
        except Exception as e:
            logger.warning(
                f"Score fetch failed for id={platform_id}/{year}: {e}"
            )
            return []

    def _parse_score_response(
        self, data: dict, year: int
    ) -> list[dict]:
        """Parse the nested score JSON into flat admission records."""
        results = []
        school_id = ""
        batches = data.get("data", {})
        if not isinstance(batches, dict):
            return results

        for _batch_key, batch_data in batches.items():
            if not isinstance(batch_data, dict):
                continue
            items = batch_data.get("item", [])
            for item in items:
                school_id = item.get("school_id", school_id)
                results.append({
                    "platform_id": school_id,
                    "major_name": item.get("sp_name", ""),
                    "major_group": item.get("sg_name", ""),
                    "year": year,
                    "province": TARGET_PROVINCE,
                    "batch": item.get("local_batch_name", "本科批"),
                    "subject_requirements": item.get("sg_info", ""),
                    "plan_count": self._parse_int(item.get("lq_num")),
                    "min_score": self._parse_int(item.get("min")),
                    "min_rank": self._parse_int(item.get("min_section")),
                    "avg_score": self._parse_int(item.get("average")),
                    "max_score": self._parse_int(item.get("max")),
                    "source_url": (
                        "https://static-data.gaokao.cn/www/2.0/"
                        f"schoolspecialscore/{school_id}/{year}/{PROVINCE_ID}.json"
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

    async def fetch_college_info(
        self, client: httpx.AsyncClient, platform_id: int
    ) -> dict | None:
        """Fetch school info from the platform."""
        url = (
            f"{self.config.base_url}/www/2.0/"
            f"school/{platform_id}/info.json"
        )
        try:
            resp = await self.fetch_with_retry(client, url)
            info = resp.get("data", {})
            if isinstance(info, dict):
                return {
                    "name": info.get("name", ""),
                    "platform_id": str(platform_id),
                    "type": _map_school_type(info.get("type", "")),
                    "level": _map_school_level(info),
                    "website": info.get("site", ""),
                    "intro": info.get("content", ""),
                    "city": info.get("city_name", ""),
                    "is_985": _to_bool(info.get("f985")),
                    "is_211": _to_bool(info.get("f211")),
                    "is_double_first": _to_bool(
                        info.get("dual_class_name")
                    ),
                }
        except Exception as e:
            logger.warning(
                f"College info fetch failed for id={platform_id}: {e}"
            )
        return None

    async def run(self) -> dict:
        """Fetch admission scores for all mapped schools × all years."""
        all_scores = []
        college_infos = []

        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            headers=self.config.headers,
            limits=httpx.Limits(max_connections=8),
        ) as client:
            # Fetch college info for known IDs
            seen_ids = set()
            total_ids = len(set(
                sid for sid in SCHOOL_ID_MAP.values() if sid > 0
            ))
            idx = 0
            for moe_code, platform_id in SCHOOL_ID_MAP.items():
                if platform_id <= 0 or platform_id in seen_ids:
                    continue
                seen_ids.add(platform_id)
                idx += 1

                info = await self.fetch_college_info(client, platform_id)
                if info:
                    info["moe_code"] = moe_code
                    college_infos.append(info)
                logger.info(
                    f"College info {idx}/{total_ids}: "
                    f"{info['name'] if info else 'FAILED'} "
                    f"(platform_id={platform_id})"
                )
                await asyncio.sleep(0.3)

            self.save_raw("colleges.json", college_infos)

            # Fetch scores: each school × each year
            sem = asyncio.Semaphore(6)
            total_tasks = len(seen_ids) * len(TARGET_YEARS)

            async def fetch_one(pid: int, year: int) -> list[dict]:
                async with sem:
                    return await self.fetch_scores(client, pid, year)

            tasks = []
            for pid in seen_ids:
                for year in TARGET_YEARS:
                    tasks.append(fetch_one(pid, year))

            logger.info(
                f"Fetching scores: {len(seen_ids)} schools × "
                f"{len(TARGET_YEARS)} years = {len(tasks)} requests..."
            )

            results = await asyncio.gather(*tasks)
            for batch in results:
                all_scores.extend(batch)

            logger.info(
                f"Collected {len(all_scores)} admission score records "
                f"({len(college_infos)} college infos)"
            )
            self.save_raw("admissions.json", all_scores)

        return {
            "source": "gaokao_scores",
            "colleges": len(college_infos),
            "admissions": len(all_scores),
        }


def _to_bool(val) -> bool:
    """Safely convert API value to bool (handles '0'/'1' strings)."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip() in ("1", "true", "True", "是", "yes")
    if isinstance(val, (int, float)):
        return bool(int(val))
    return bool(val)


def _map_school_type(type_code: str) -> str:
    """Map platform type code to Chinese category name."""
    type_map = {
        "5001": "综合", "5002": "理工", "5003": "农林",
        "5004": "医药", "5005": "师范", "5006": "语言",
        "5007": "财经", "5008": "政法", "5009": "体育",
        "5010": "艺术", "5011": "民族",
    }
    return type_map.get(type_code, "综合")


def _map_school_level(info: dict) -> str:
    """Determine school level from platform flags."""
    if _to_bool(info.get("f985")):
        return "985"
    if _to_bool(info.get("f211")):
        return "211"
    if _to_bool(info.get("dual_class_name")):
        return "双一流"
    nature = info.get("school_nature", "")
    nature_map = {
        "36000": "省重点",
        "36001": "普通本科",
        "36002": "独立学院",
        "36003": "民办本科",
    }
    return nature_map.get(str(nature), "省重点")
