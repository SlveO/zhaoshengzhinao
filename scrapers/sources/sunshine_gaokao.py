"""阳光高考 (gaokao.chsi.com.cn) scraper — authoritative school & major data."""
import re
import httpx
from bs4 import BeautifulSoup
from loguru import logger

from scrapers.config import (
    ScraperConfig, GUANGDONG_UNIVERSITIES, TARGET_PROVINCE,
)
from scrapers.base_scraper import BaseScraper


class SunshineGaokaoScraper(BaseScraper):
    """Scrapes 阳光高考 for official college profiles and major catalogs."""

    def __init__(self):
        super().__init__(ScraperConfig(
            name="sunshine_gaokao",
            base_url="https://gaokao.chsi.com.cn",
            delay_seconds=2.0,
        ))

    async def fetch_college_page(
        self, client: httpx.AsyncClient, code: str
    ) -> BeautifulSoup | None:
        """Fetch a school's detail page and return parsed HTML."""
        url = f"{self.config.base_url}/sch/schoolInfoMain--schId-{code}.dhtml"
        try:
            html = await self.fetch_with_retry(client, url, expect_json=False)
            return BeautifulSoup(html, "html.parser")
        except Exception as e:
            logger.warning(f"Failed college page for {code}: {e}")
            return None

    def parse_college_info(self, soup: BeautifulSoup, code: str) -> dict:
        """Extract structured college info from HTML page."""
        info = {"code": code}
        try:
            name_el = soup.find("h1") or soup.find("h2")
            if name_el:
                info["name"] = name_el.get_text(strip=True)

            intro_div = soup.find("div", class_="intro") or soup.find(
                "div", string=re.compile("院校简介|学校简介")
            )
            if intro_div:
                info["intro"] = intro_div.get_text(strip=True)[:2000]

            for row in soup.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    if "主管部门" in key:
                        info["governing_body"] = val
                    elif "地址" in key:
                        info["address"] = val
                    elif "网址" in key:
                        info["website"] = val
                    elif "创建时间" in key:
                        nums = re.findall(r"\d+", val)
                        if nums:
                            info["founded_year"] = int(nums[0])
        except Exception as e:
            logger.warning(f"Parse error for college {code}: {e}")
        return info

    async def fetch_major_list(
        self, client: httpx.AsyncClient, code: str
    ) -> list[dict]:
        """Fetch major catalog for one school with status detection."""
        url = f"{self.config.base_url}/sch/majorList--schId-{code}.dhtml"
        try:
            html = await self.fetch_with_retry(client, url, expect_json=False)
            soup = BeautifulSoup(html, "html.parser")
            majors = []
            for row in soup.select("table tr")[1:]:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    major = {
                        "college_code": code,
                        "major_name": cells[0].get_text(strip=True),
                        "category": (cells[1].get_text(strip=True)
                                      if len(cells) > 1 else ""),
                        "degree_type": (cells[2].get_text(strip=True)
                                         if len(cells) > 2 else ""),
                        "duration": (int(cells[3].get_text(strip=True))
                                      if len(cells) > 3 and
                                      cells[3].get_text(strip=True).isdigit()
                                      else 4),
                        "status": "active",
                    }
                    cell_text = " ".join(
                        c.get_text(strip=True) for c in cells
                    )
                    if "新增" in cell_text or "新设" in cell_text:
                        major["status"] = "new"
                    elif "停招" in cell_text or "撤销" in cell_text:
                        major["status"] = "discontinued"
                    majors.append(major)
            return majors
        except Exception as e:
            logger.warning(f"Failed major list for {code}: {e}")
            return []

    async def run(self) -> dict:
        """Collect official college and major data from 阳光高考."""
        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            headers=self.config.headers,
        ) as client:
            all_college_info = []
            all_majors = []

            for uni in GUANGDONG_UNIVERSITIES:
                code = uni["code"]
                soup = await self.fetch_college_page(client, code)
                if soup:
                    info = self.parse_college_info(soup, code)
                    all_college_info.append({**uni, **info})

                majors = await self.fetch_major_list(client, code)
                all_majors.extend(majors)

            self.save_raw("college_details.json", all_college_info)
            self.save_raw("major_catalog.json", all_majors)

        return {
            "source": "sunshine_gaokao",
            "college_details": len(all_college_info),
            "majors": len(all_majors),
        }
