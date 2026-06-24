"""SCNU admissions scraper - extract tables from official zsb.scnu.edu.cn PDFs.

Source: https://zsb.scnu.edu.cn/zhiyuancankao/
Coverage: 2022-2025, Guangdong + other provinces
"""
import asyncio, httpx, pdfplumber, re
from io import BytesIO
from bs4 import BeautifulSoup
from loguru import logger

from scrapers.config import ScraperConfig, DATA_RAW
from scrapers.base_scraper import BaseScraper

ZSB_BASE = "https://zsb.scnu.edu.cn"
ZHIYUAN_URL = f"{ZSB_BASE}/zhiyuancankao/"


def _extract_pdf_urls(html_text):
    """Extract PDF URLs from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html_text, "html.parser")
    urls = []

    for tag_name, attr in [("iframe", "src"), ("a", "href"), ("img", "src")]:
        for tag in soup.find_all(tag_name):
            val = tag.get(attr, "")
            if val:
                urls.append(val)

    text_matches = re.findall(r'(?:https?:)?//[^\s"\'<>]+\.pdf', html_text)

    pdfs = []
    for u in urls + text_matches:
        base = u.split("#")[0].split("?")[0]
        if not base.lower().endswith(".pdf"):
            continue
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            u = ZSB_BASE + u
        elif not u.startswith("http"):
            u = ZSB_BASE + "/" + u
        pdfs.append(u)

    return pdfs


class SCNUZsbAdmissionsScraper(BaseScraper):

    def __init__(self):
        super().__init__(ScraperConfig(
            name="scnu_zsb",
            base_url=ZSB_BASE,
            delay_seconds=2.0,
        ))

    async def _get_year_map(self, client):
        """Scrape zhiyuancankao/ for year URLs."""
        r = await self.fetch_with_retry(client, ZHIYUAN_URL, expect_json=False)
        soup = BeautifulSoup(r, "html.parser")

        year_map = {}
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if not href.startswith("http"):
                href = ZSB_BASE + href

            m = re.match(r"(\d{4})年华南师范大学(.+?)录取情况", text)
            if not m:
                continue
            year = int(m.group(1))
            region = m.group(2)
            if year < 2022 or year > 2025:
                continue

            if year not in year_map:
                year_map[year] = {}

            if "广东" in region:
                year_map[year]["guangdong_url"] = href
            elif "外省" in region or "全国" in region:
                if "外省" in region:
                    year_map[year]["waisheng_url"] = href
                elif "全国" in region and "waisheng_url" not in year_map[year]:
                    year_map[year]["waisheng_url"] = href

        logger.info(f"Found {len(year_map)} years: {sorted(year_map.keys())}")
        return year_map

    async def _find_pdf_url(self, client, article_url):
        """Extract the first real PDF link from an article page."""
        try:
            r = await self.fetch_with_retry(client, article_url, expect_json=False)
        except Exception as e:
            logger.warning(f"Failed to fetch article {article_url}: {e}")
            return None

        all_pdfs = _extract_pdf_urls(r)
        real_pdfs = [u for u in all_pdfs if "viewer" not in u.lower() and "/pics/" in u]
        return real_pdfs[0] if real_pdfs else (all_pdfs[0] if all_pdfs else None)

    def _parse_pdf_table(self, pdf_bytes, year, province_type):
        """Extract admissions rows from a PDF. Skips rows with wrong column count."""
        results = []
        MIN_COLS = 10  # minimum expected columns

        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        current = {"province_code": "", "province": "", "batch": "", "category": ""}
                        for row in table:
                            if not row or not any(row):
                                continue

                            # Skip rows with too few columns
                            non_none = [c for c in row if c is not None]
                            if len(non_none) < MIN_COLS:
                                continue

                            # Skip header rows
                            if row[0] and "省市" in str(row[0]):
                                continue

                            # Safely get column values
                            def _cell(idx, default=""):
                                try:
                                    val = row[idx]
                                    return str(val).strip() if val else default
                                except IndexError:
                                    return default

                            # Update context from non-None cells
                            if row[0] and str(row[0]).strip():
                                current["province_code"] = _cell(0)
                            if row[1] and str(row[1]).strip():
                                prov = _cell(1)
                                if "合 计" not in prov:
                                    current["province"] = prov
                            if len(row) > 2 and row[2] and str(row[2]).strip():
                                current["batch"] = _cell(2)
                            if len(row) > 3 and row[3] and str(row[3]).strip():
                                current["category"] = _cell(3)

                            major = _cell(6)
                            if not major or "合 计" in major:
                                continue

                            def _s(k):
                                try:
                                    return int(float(_cell(k).replace(",", "")))
                                except Exception:
                                    return None

                            results.append({
                                "year": year,
                                "province_code": current["province_code"],
                                "province": current["province"],
                                "batch": current["batch"],
                                "category": current["category"],
                                "campus": _cell(4),
                                "college": _cell(5),
                                "major": major,
                                "subject_requirements": _cell(7),
                                "plan_count": _s(8),
                                "max_score": _s(9),
                                "avg_score": _s(10) if len(row) > 10 else None,
                                "min_score": _s(11) if len(row) > 11 else _s(10),
                                "college_code": "10574",
                                "college_name": "华南师范大学",
                            })

            logger.info(f"  Parsed {len(results)} rows from PDF ({year} {province_type})")
        except Exception as e:
            logger.error(f"  PDF parse failed ({year} {province_type}): {type(e).__name__}: {e}")
        return results

    async def run(self):
        all_records = []
        errors = []

        async with httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/pdf,application/json,*/*",
            },
            follow_redirects=True,
        ) as client:
            year_map = await self._get_year_map(client)

            for year in sorted(year_map.keys()):
                info = year_map[year]
                for ptype, url_key in [("guangdong", "guangdong_url"), ("waisheng", "waisheng_url")]:
                    if url_key not in info:
                        continue
                    article_url = info[url_key]
                    logger.info(f"Processing {year} {ptype}: {article_url}")

                    pdf_url = await self._find_pdf_url(client, article_url)
                    if not pdf_url:
                        errors.append({"year": year, "type": ptype, "error": "no PDF found"})
                        logger.warning(f"  No PDF found for {year} {ptype}")
                        continue

                    logger.info(f"  PDF: {pdf_url}")
                    try:
                        pdf_resp = await client.get(pdf_url)
                        pdf_resp.raise_for_status()
                        raw_bytes = pdf_resp.content
                    except Exception as e:
                        errors.append({"year": year, "type": ptype, "error": str(e)})
                        continue

                    records = self._parse_pdf_table(raw_bytes, year, ptype)
                    all_records.extend(records)

        out_path = self.save_raw("admissions_scnu.json", all_records)
        if errors:
            self.save_raw("errors_admissions_scnu.json", errors)

        logger.info(f"Done: {len(all_records)} records, {len(errors)} errors, output: {out_path}")
        return {
            "source": "scnu_zsb_admissions",
            "records": len(all_records),
            "errors": len(errors),
            "output": str(out_path),
        }


if __name__ == "__main__":
    asyncio.run(SCNUZsbAdmissionsScraper().run())
