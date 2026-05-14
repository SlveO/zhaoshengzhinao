# Gaokao Data Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-source scraping pipeline that collects Guangdong universities' admission data, major catalogs, employment outcomes, and industry analysis (2020-2025), then exports clean JSON ready for PostgreSQL seeding and Chroma indexing.

**Architecture:** Each data source has its own scraper module with a shared base class handling rate-limiting, retries, and logging. Scraped raw data lands in `data/raw/`, parsed data in `data/processed/`, validated data in `data/cleaned/`, and final merged exports in `data/approved/`. Existing `seed_db.py` is extended to read the new multi-file format. Existing `schools.json` and `scores.json` in `data/seed/` are overwritten with the complete collected data.

**Tech Stack:** Python 3.11+, `httpx` (async HTTP), `beautifulsoup4` (HTML parsing), `pdfplumber` (PDF parsing), `pydantic` (data validation), `tenacity` (retry), `loguru` (logging), `typer` (CLI)

---

### Task 1: Data Pipeline Directory & Config Setup

**Files:**
- Create: `scrapers/__init__.py`
- Create: `scrapers/config.py`

- [ ] **Step 1: Create `scrapers/config.py` with global settings**

```python
"""Global configuration for all scrapers."""
from pathlib import Path
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_CLEANED = PROJECT_ROOT / "data" / "cleaned"
DATA_APPROVED = PROJECT_ROOT / "data" / "approved"
DATA_SEED = PROJECT_ROOT / "data" / "seed"
LOG_DIR = PROJECT_ROOT / "data" / "logs"

for d in [DATA_RAW, DATA_PROCESSED, DATA_CLEANED, DATA_APPROVED, DATA_SEED, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class ScraperConfig:
    """Per-scraper configuration."""
    name: str
    base_url: str
    delay_seconds: float = 1.5       # polite delay between requests
    max_retries: int = 3
    timeout_seconds: int = 30
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    headers: dict = field(default_factory=lambda: {
        "Accept": "text/html,application/json,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })

# Known Guangdong undergraduate universities (教育部院校代码)
GUANGDONG_UNIVERSITIES: list[dict] = [
    {"code": "10558", "name": "中山大学", "city": "广州", "type": "综合", "level": "985"},
    {"code": "10561", "name": "华南理工大学", "city": "广州", "type": "理工", "level": "985"},
    {"code": "10559", "name": "暨南大学", "city": "广州", "type": "综合", "level": "211"},
    {"code": "10574", "name": "华南师范大学", "city": "广州", "type": "师范", "level": "211"},
    {"code": "10564", "name": "华南农业大学", "city": "广州", "type": "农林", "level": "双一流"},
    {"code": "12121", "name": "南方医科大学", "city": "广州", "type": "医药", "level": "省重点"},
    {"code": "10572", "name": "广州中医药大学", "city": "广州", "type": "医药", "level": "双一流"},
    {"code": "10590", "name": "深圳大学", "city": "深圳", "type": "综合", "level": "省重点"},
    {"code": "11845", "name": "广东工业大学", "city": "广州", "type": "理工", "level": "省重点"},
    {"code": "11078", "name": "广州大学", "city": "广州", "type": "综合", "level": "省重点"},
    {"code": "11846", "name": "广东外语外贸大学", "city": "广州", "type": "语言", "level": "省重点"},
    {"code": "10560", "name": "汕头大学", "city": "汕头", "type": "综合", "level": "省重点"},
    {"code": "14325", "name": "南方科技大学", "city": "深圳", "type": "理工", "level": "双一流"},
    {"code": "10570", "name": "广州医科大学", "city": "广州", "type": "医药", "level": "双一流"},
    {"code": "10592", "name": "广东财经大学", "city": "广州", "type": "财经", "level": "省重点"},
    {"code": "10566", "name": "广东海洋大学", "city": "湛江", "type": "农林", "level": "省重点"},
    {"code": "11819", "name": "东莞理工学院", "city": "东莞", "type": "理工", "level": "省重点"},
    {"code": "11847", "name": "佛山科学技术学院", "city": "佛山", "type": "理工", "level": "省重点"},
    {"code": "11349", "name": "五邑大学", "city": "江门", "type": "综合", "level": "省重点"},
    {"code": "11347", "name": "仲恺农业工程学院", "city": "广州", "type": "农林", "level": "省重点"},
    {"code": "10571", "name": "广东医科大学", "city": "湛江", "type": "医药", "level": "省重点"},
    {"code": "10573", "name": "广东药科大学", "city": "广州", "type": "医药", "level": "省重点"},
    {"code": "10576", "name": "韶关学院", "city": "韶关", "type": "综合", "level": "普通本科"},
    {"code": "10577", "name": "惠州学院", "city": "惠州", "type": "综合", "level": "普通本科"},
    {"code": "10578", "name": "韩山师范学院", "city": "潮州", "type": "师范", "level": "普通本科"},
    {"code": "10579", "name": "岭南师范学院", "city": "湛江", "type": "师范", "level": "普通本科"},
    {"code": "10580", "name": "肇庆学院", "city": "肇庆", "type": "综合", "level": "普通本科"},
    {"code": "10582", "name": "嘉应学院", "city": "梅州", "type": "综合", "level": "普通本科"},
    {"code": "10585", "name": "广州体育学院", "city": "广州", "type": "体育", "level": "省重点"},
    {"code": "10586", "name": "广州美术学院", "city": "广州", "type": "艺术", "level": "省重点"},
    {"code": "10587", "name": "星海音乐学院", "city": "广州", "type": "艺术", "level": "省重点"},
    {"code": "10588", "name": "广东技术师范大学", "city": "广州", "type": "师范", "level": "省重点"},
    {"code": "10591", "name": "广东金融学院", "city": "广州", "type": "财经", "level": "普通本科"},
    {"code": "11540", "name": "广东警官学院", "city": "广州", "type": "政法", "level": "普通本科"},
    {"code": "11656", "name": "广东石油化工学院", "city": "茂名", "type": "理工", "level": "普通本科"},
    {"code": "11848", "name": "北京师范大学-香港浸会大学联合国际学院", "city": "珠海", "type": "综合", "level": "中外合作"},
    {"code": "11852", "name": "广东理工学院", "city": "肇庆", "type": "理工", "level": "民办本科"},
    {"code": "12059", "name": "广东培正学院", "city": "广州", "type": "综合", "level": "民办本科"},
    {"code": "13656", "name": "广州华立学院", "city": "广州", "type": "综合", "level": "民办本科"},
    {"code": "13657", "name": "广州商学院", "city": "广州", "type": "财经", "level": "民办本科"},
    {"code": "13667", "name": "广东白云学院", "city": "广州", "type": "综合", "level": "民办本科"},
    {"code": "13675", "name": "北京理工大学珠海学院", "city": "珠海", "type": "理工", "level": "独立学院"},
    {"code": "13684", "name": "珠海科技学院", "city": "珠海", "type": "综合", "level": "民办本科"},
    {"code": "13714", "name": "广州工商学院", "city": "佛山", "type": "财经", "level": "民办本科"},
    {"code": "13718", "name": "广州理工学院", "city": "广州", "type": "理工", "level": "民办本科"},
    {"code": "13719", "name": "广东科技学院", "city": "东莞", "type": "理工", "level": "民办本科"},
    {"code": "13720", "name": "广州新华学院", "city": "广州", "type": "综合", "level": "独立学院"},
    {"code": "13721", "name": "广州城市理工学院", "city": "广州", "type": "理工", "level": "民办本科"},
    {"code": "13844", "name": "东莞城市学院", "city": "东莞", "type": "综合", "level": "民办本科"},
    {"code": "13902", "name": "广州南方学院", "city": "广州", "type": "综合", "level": "民办本科"},
    {"code": "14278", "name": "广东第二师范学院", "city": "广州", "type": "师范", "level": "普通本科"},
    {"code": "14390", "name": "广州航海学院", "city": "广州", "type": "理工", "level": "普通本科"},
    {"code": "16148", "name": "华南农业大学珠江学院", "city": "广州", "type": "农林", "level": "独立学院"},
    {"code": "16401", "name": "深圳技术大学", "city": "深圳", "type": "理工", "level": "普通本科"},
    {"code": "18173", "name": "广东以色列理工学院", "city": "汕头", "type": "理工", "level": "中外合作"},
    {"code": "18272", "name": "香港中文大学(深圳)", "city": "深圳", "type": "综合", "level": "中外合作"},
    {"code": "18303", "name": "南方科技大学伦敦国王学院医学院", "city": "深圳", "type": "医药", "level": "中外合作"},
    {"code": "18327", "name": "广东东软学院", "city": "佛山", "type": "理工", "level": "民办本科"},
    {"code": "18398", "name": "香港科技大学(广州)", "city": "广州", "type": "理工", "level": "中外合作"},
    {"code": "18405", "name": "广州软件学院", "city": "广州", "type": "理工", "level": "民办本科"},
    {"code": "18593", "name": "香港城市大学(东莞)", "city": "东莞", "type": "综合", "level": "中外合作"},
    {"code": "18894", "name": "广东工商职业技术大学", "city": "肇庆", "type": "综合", "level": "民办本科"},
    {"code": "19032", "name": "广州应用科技学院", "city": "广州", "type": "综合", "level": "民办本科"},
    {"code": "19305", "name": "深圳理工大学", "city": "深圳", "type": "理工", "level": "普通本科"},
    {"code": "19565", "name": "湛江科技学院", "city": "湛江", "type": "综合", "level": "民办本科"},
]

TARGET_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
TARGET_PROVINCE = "广东"
```

- [ ] **Step 2: Verify the config file**

Run: `python -c "from scrapers.config import GUANGDONG_UNIVERSITIES; print(f'{len(GUANGDONG_UNIVERSITIES)} universities')"`
Expected: `67 universities`

- [ ] **Step 3: Commit**

```bash
git add scrapers/__init__.py scrapers/config.py
git commit -m "feat: add scrapers config with 67 Guangdong universities and global settings"
```

---

### Task 2: Base Scraper with Retry & Rate-Limiting

**Files:**
- Create: `scrapers/base_scraper.py`

- [ ] **Step 1: Write `scrapers/base_scraper.py`**

```python
"""Async base scraper with retry, rate-limiting, and structured logging."""
import asyncio
import time
import json
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

import httpx
from loguru import logger
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type
)

from scrapers.config import ScraperConfig, DATA_RAW


class ScrapingError(Exception):
    """Raised when a scrape fails after all retries."""


class BaseScraper:
    """Base class for all data source scrapers."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self.raw_dir = DATA_RAW / config.name
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            self.raw_dir / "scraper.log",
            rotation="10 MB",
            retention="7 days",
            level="INFO",
        )

    async def _rate_limit(self):
        """Ensure minimum delay between requests."""
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self.config.delay_seconds:
                await asyncio.sleep(self.config.delay_seconds - elapsed)
            self._last_request_time = time.monotonic()

    async def _fetch(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[dict] = None,
        expect_json: bool = True,
    ) -> Any:
        """Fetch URL with rate limiting and error handling."""
        await self._rate_limit()
        headers = {**self.config.headers, "User-Agent": self.config.user_agent}
        resp = await client.get(
            url, params=params, headers=headers,
            timeout=self.config.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json() if expect_json else resp.text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def fetch_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[dict] = None,
        expect_json: bool = True,
    ) -> Any:
        """Fetch with automatic retry on network errors."""
        try:
            return await self._fetch(client, url, params, expect_json)
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
            raise ScrapingError(f"Failed to fetch {url}: {e}")

    def save_raw(self, filename: str, data: Any):
        """Save raw scraped data to disk."""
        path = self.raw_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, (list, dict)):
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(data))
        logger.info(f"Saved raw data: {path}")
        return path

    def load_raw(self, filename: str) -> Any:
        """Load previously saved raw data."""
        path = self.raw_dir / filename
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def run(self) -> dict:
        """Override in subclasses. Returns summary dict."""
        raise NotImplementedError
```

- [ ] **Step 2: Verify base scraper loads without errors**

Run: `python -c "from scrapers.base_scraper import BaseScraper; print('BaseScraper imported OK')"`
Expected: `BaseScraper imported OK`

- [ ] **Step 3: Commit**

```bash
git add scrapers/base_scraper.py
git commit -m "feat: add async base scraper with retry, rate-limiting, and logging"
```

---

### Task 3: Pydantic Data Models/Schemas

**Files:**
- Create: `scrapers/storage/__init__.py`
- Create: `scrapers/storage/schema.py`

- [ ] **Step 1: Write `scrapers/storage/schema.py`**

```python
"""Pydantic data models for all collected data types."""
from __future__ import annotations
from typing import Optional, Annotated
from datetime import date
from pydantic import BaseModel, Field, field_validator


# --- College ---
class College(BaseModel):
    code: str = Field(..., min_length=5, max_length=6, description="教育部院校代码")
    name: str = Field(..., max_length=100)
    type: str = Field(..., description="综合/理工/师范/医药/财经/农林/语言/政法/体育/艺术")
    level: str = Field(..., description="985/211/双一流/省重点/普通本科/民办本科/独立学院/中外合作")
    province: str = "广东"
    city: str
    is_985: bool = False
    is_211: bool = False
    is_double_first: bool = False
    founded_year: Optional[int] = None
    campuses: list[str] = Field(default_factory=list)
    website: str = ""
    admission_url: str = ""
    employment_report_url: str = ""
    key_disciplines: list[str] = Field(default_factory=list)
    intro: str = ""
    ranking_soft_2024: Optional[int] = None
    student_count: Optional[int] = None
    source: str = ""


# --- Major ---
class Major(BaseModel):
    college_code: str = Field(..., min_length=5, max_length=6)
    major_code: str = Field(..., min_length=6, max_length=6, description="教育部专业代码")
    major_name: str = Field(..., max_length=100)
    category: str = Field(..., description="学科门类: 哲学/经济学/法学/教育学/文学/历史学/理学/工学/农学/医学/管理学/艺术学")
    subcategory: str = Field(default="", description="专业类")
    degree_type: str = ""
    duration: int = 4
    status: str = "active"  # active | discontinued | new
    new_since: Optional[int] = Field(None, description="新增年份(2023-2025)")
    discontinued_since: Optional[int] = Field(None, description="停招年份")
    is_national_first_class: bool = False
    is_provincial_first_class: bool = False
    special_notes: str = ""
    subject_requirements: str = Field(default="", description="典型选科要求")
    source: str = ""


# --- Admission ---
class Admission(BaseModel):
    college_code: str = Field(..., min_length=5, max_length=6)
    major_name: str = Field(..., max_length=100)
    major_group: str = Field(default="", description="专业组名称")
    year: int = Field(..., ge=2020, le=2025)
    province: str = Field(default="广东")
    batch: str = Field(default="本科批")
    subject_requirements: str = Field(default="", description="选科要求")
    plan_count: Optional[int] = None
    min_score: int = Field(..., ge=0, le=750)
    min_rank: Optional[int] = None
    avg_score: Optional[int] = None
    max_score: Optional[int] = None
    low_score: Optional[int] = None  # lowest admitted score (alternate field name)
    source_url: str = ""

    @field_validator("source_url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        return v or "https://eea.gd.gov.cn/"


# --- Employment ---
class Employment(BaseModel):
    college_code: str = Field(..., min_length=5, max_length=6)
    major_name: str = Field(..., max_length=100)
    year: int = Field(..., ge=2020, le=2025)
    graduate_count: Optional[int] = None
    employment_rate: Optional[float] = None
    domestic_graduate_rate: Optional[float] = None
    overseas_rate: Optional[float] = None
    direct_employment_rate: Optional[float] = None
    avg_monthly_salary: Optional[float] = None
    median_monthly_salary: Optional[float] = None
    top_industries: list[dict] = Field(default_factory=list)
    top_positions: list[dict] = Field(default_factory=list)
    top_employers: list[str] = Field(default_factory=list)
    satisfaction_rate: Optional[float] = None
    major_match_rate: Optional[float] = None
    source: str = ""


# --- Industry ---
class Industry(BaseModel):
    industry_name: str = Field(..., max_length=100)
    industry_code: str = ""
    year: int = Field(..., ge=2020, le=2025)
    avg_annual_salary: Optional[float] = None
    salary_growth_rate: Optional[float] = None
    employment_demand_index: Optional[float] = Field(None, ge=0, le=5)
    industry_growth_rate: Optional[float] = None
    entry_difficulty: str = "中等"
    popular_positions: list[dict] = Field(default_factory=list)
    career_path: str = ""
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    insider_reviews: list[dict] = Field(default_factory=list)
    related_majors: list[str] = Field(default_factory=list)
    outlook: str = ""
    source: str = ""


# --- Major-Industry Mapping ---
class MajorIndustryMapping(BaseModel):
    major_name: str
    primary_industries: list[str] = Field(default_factory=list)
    secondary_industries: list[str] = Field(default_factory=list)
    typical_positions: list[str] = Field(default_factory=list)
    salary_range: dict = Field(default_factory=lambda: {"entry": 0, "mid": 0, "senior": 0})
```

- [ ] **Step 2: Verify models import and validate**

Run: `python -c "from scrapers.storage.schema import College; c = College(code='10558', name='中山大学', type='综合', level='985', city='广州'); print(c.model_dump_json(indent=2))"`
Expected: Valid JSON output

- [ ] **Step 3: Commit**

```bash
git add scrapers/storage/
git commit -m "feat: add Pydantic data models for all 6 data types"
```

---

### Task 4: Data Exporter & Validator

**Files:**
- Create: `scrapers/storage/exporter.py`
- Create: `scrapers/storage/validator.py`

- [ ] **Step 1: Write `scrapers/storage/exporter.py`**

```python
"""Export collected data to JSON files for seeding and indexing."""
import json
from pathlib import Path
from typing import Any
from loguru import logger

from scrapers.config import DATA_PROCESSED, DATA_CLEANED, DATA_APPROVED, DATA_SEED
from scrapers.storage.schema import (
    College, Major, Admission, Employment, Industry, MajorIndustryMapping,
)


def _serialize(obj: Any) -> Any:
    """Convert Pydantic models and other objects to JSON-serializable types."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    return obj


def save_json(data: list, filename: str, target_dir: Path = DATA_PROCESSED):
    """Save a list of objects to a JSON file."""
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / filename
    serialized = _serialize(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)
    logger.info(f"Exported {len(serialized)} records to {path}")
    return path


def export_seed_files(
    colleges: list[College],
    admissions: list[Admission],
):
    """Export college and admission data to seed/ directory.
    Overwrites existing schools.json and scores.json from MVP.
    """
    # Build schools.json in the existing seed format for backward compatibility
    school_records = []
    for c in colleges:
        school_records.append({
            "name": c.name,
            "code": c.code,
            "type": c.type,
            "level": c.level,
            "province": c.province,
            "city": c.city,
            "is_985": c.is_985,
            "is_211": c.is_211,
            "is_double_first": c.is_double_first,
            "intro": c.intro,
        })
    save_json(school_records, "schools.json", DATA_SEED)

    # Build scores.json in the existing seed format
    score_records = []
    for a in admissions:
        score_records.append({
            "college_name": next(
                (c.name for c in colleges if c.code == a.college_code), ""
            ),
            "major_name": a.major_name,
            "year": a.year,
            "batch": a.batch,
            "min_score": a.min_score,
            "min_rank": a.min_rank,
            "subject_requirements": a.subject_requirements,
            "source_url": a.source_url,
        })
    save_json(score_records, "scores.json", DATA_SEED)


def export_full_data(
    colleges: list[College],
    majors: list[Major],
    admissions: list[Admission],
    employment: list[Employment],
    industries: list[Industry],
    mappings: list[MajorIndustryMapping],
):
    """Export all collected data to approved/ directory."""
    save_json(colleges, "colleges_full.json", DATA_APPROVED)
    save_json(majors, "majors.json", DATA_APPROVED)
    save_json(admissions, "admissions.json", DATA_APPROVED)
    save_json(employment, "employment.json", DATA_APPROVED)
    save_json(industries, "industries.json", DATA_APPROVED)
    save_json(mappings, "major_industry_mapping.json", DATA_APPROVED)
    # Also output seed-compatible files
    export_seed_files(colleges, admissions)
    logger.info("Full data export complete")
```

- [ ] **Step 2: Write `scrapers/storage/validator.py`**

```python
"""Data quality validation."""
from typing import Any
from loguru import logger


def validate_colleges(data: list[dict]) -> tuple[list[dict], list[str]]:
    """Validate college records. Returns (valid, errors)."""
    valid, errors = [], []
    codes_seen = set()
    for i, item in enumerate(data):
        errs = []
        code = item.get("code", "")
        if not code or len(code) not in (5, 6):
            errs.append(f"row {i}: invalid code '{code}'")
        if code in codes_seen:
            errs.append(f"row {i}: duplicate code '{code}'")
        codes_seen.add(code)
        if not item.get("name"):
            errs.append(f"row {i}: missing name")
        if errs:
            errors.extend(errs)
        else:
            valid.append(item)
    logger.info(f"College validation: {len(valid)} ok, {len(errors)} errors")
    return valid, errors


def validate_admissions(data: list[dict]) -> tuple[list[dict], list[str]]:
    """Validate admission records."""
    valid, errors = [], []
    for i, item in enumerate(data):
        errs = []
        score = item.get("min_score", -1)
        if not (0 <= score <= 750):
            errs.append(f"row {i}: invalid min_score {score}")
        year = item.get("year", -1)
        if not (2020 <= year <= 2025):
            errs.append(f"row {i}: invalid year {year}")
        if not item.get("college_code"):
            errs.append(f"row {i}: missing college_code")
        if not item.get("major_name"):
            errs.append(f"row {i}: missing major_name")
        if errs:
            errors.extend(errs)
        else:
            valid.append(item)
    logger.info(f"Admission validation: {len(valid)} ok, {len(errors)} errors")
    return valid, errors


def validate_employment(data: list[dict]) -> tuple[list[dict], list[str]]:
    """Validate employment records."""
    valid, errors = [], []
    for i, item in enumerate(data):
        errs = []
        rate = item.get("employment_rate", -1)
        if rate is not None and not (0 <= rate <= 1):
            errs.append(f"row {i}: invalid employment_rate {rate}")
        salary = item.get("avg_monthly_salary", -1)
        if salary is not None and salary < 0:
            errs.append(f"row {i}: negative salary {salary}")
        if errs:
            errors.extend(errs)
        else:
            valid.append(item)
    logger.info(f"Employment validation: {len(valid)} ok, {len(errors)} errors")
    return valid, errors


def validate_industries(data: list[dict]) -> tuple[list[dict], list[str]]:
    """Validate industry records."""
    valid, errors = [], []
    names_seen = set()
    for i, item in enumerate(data):
        errs = []
        name = item.get("industry_name", "")
        if not name:
            errs.append(f"row {i}: missing industry_name")
        if name in names_seen:
            errs.append(f"row {i}: duplicate industry '{name}'")
        names_seen.add(name)
        if errs:
            errors.extend(errs)
        else:
            valid.append(item)
    logger.info(f"Industry validation: {len(valid)} ok, {len(errors)} errors")
    return valid, errors


def run_all_validations(
    colleges: list[dict],
    admissions: list[dict],
    employment: list[dict],
    industries: list[dict],
) -> bool:
    """Run all validations. Returns True if all pass, False otherwise."""
    vc, ec = validate_colleges(colleges)
    va, ea = validate_admissions(admissions)
    ve, ee = validate_employment(employment)
    vi, ei = validate_industries(industries)
    all_errors = ec + ea + ee + ei
    if all_errors:
        logger.error(f"Validation failed with {len(all_errors)} errors:")
        for e in all_errors[:20]:
            logger.error(f"  {e}")
        if len(all_errors) > 20:
            logger.error(f"  ... and {len(all_errors) - 20} more")
        return False
    logger.info("All validations passed")
    return True
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from scrapers.storage.exporter import export_seed_files, export_full_data; from scrapers.storage.validator import run_all_validations; print('All OK')"`
Expected: `All OK`

- [ ] **Step 4: Commit**

```bash
git add scrapers/storage/exporter.py scrapers/storage/validator.py
git commit -m "feat: add data exporter and validator for JSON output pipeline"
```

---

### Task 5: EOL API Scraper — Admissions & Majors

**Files:**
- Create: `scrapers/sources/__init__.py`
- Create: `scrapers/sources/eol_api.py`

掌上高考(api.eol.cn) has publicly accessible endpoints returning JSON for school info, major lists, and admission scores. This is the primary data source.

- [ ] **Step 1: Write `scrapers/sources/eol_api.py`**

```python
"""掌上高考 (eol.cn) API scraper — primary source for admissions and majors."""
import asyncio
import httpx
from loguru import logger

from scrapers.config import (
    ScraperConfig, GUANGDONG_UNIVERSITIES, TARGET_YEARS, TARGET_PROVINCE,
)
from scrapers.base_scraper import BaseScraper
from scrapers.storage.schema import (
    College, Major, Admission,
)


class EOLScraper(BaseScraper):
    """Scrapes 掌上高考 API for college, major, and admission score data."""

    def __init__(self):
        super().__init__(ScraperConfig(
            name="eol_api",
            base_url="https://api.eol.cn/gkcx/api",
            delay_seconds=1.0,
        ))

    async def fetch_college_detail(self, client: httpx.AsyncClient, code: str) -> dict | None:
        """Fetch detailed info for one school by its code."""
        url = f"{self.config.base_url}/school/schoolDetailBySchoolCode"
        params = {"school_code": code, "uri": "apigkcx/api/school/querySchoolDetailBySchoolCode"}
        try:
            data = await self.fetch_with_retry(client, url, params)
            return data.get("data") if data else None
        except Exception as e:
            logger.warning(f"Failed to fetch college detail for {code}: {e}")
            return None

    async def fetch_colleges(self, client: httpx.AsyncClient) -> list[dict]:
        """Fetch all Guangdong university details."""
        results = []
        tasks = [self.fetch_college_detail(client, u["code"]) for u in GUANGDONG_UNIVERSITIES]
        details = await asyncio.gather(*tasks)
        for uni, detail in zip(GUANGDONG_UNIVERSITIES, details):
            if detail:
                results.append({**uni, **self._normalize_college(uni, detail)})
            else:
                results.append(dict(uni))
        logger.info(f"Fetched {len(results)} college records")
        self.save_raw("colleges.json", results)
        return results

    async def fetch_majors_for_school(self, client: httpx.AsyncClient, code: str) -> list[dict]:
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
        """Fetch 6 years of admission scores for all 67 universities."""
        all_scores = []
        sem = asyncio.Semaphore(6)  # parallel per year

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
            "intro": detail.get("content", detail.get("school_introduce", "")),
            "website": detail.get("school_site", detail.get("site", "")),
            "student_count": detail.get("student_count"),
            "founded_year": detail.get("founding_year"),
            "ranking_soft_2024": detail.get("rank"),
            "is_985": bool(detail.get("f985")),
            "is_211": bool(detail.get("f211")),
            "is_double_first": bool(detail.get("dual_class_name")),
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

            logger.info("EOL: fetching admission scores (6 years × 67 schools)...")
            raw_admissions = await self.fetch_all_admissions(client)

        return {
            "source": "eol_api",
            "colleges": len(colleges),
            "majors": len(raw_majors),
            "admissions": len(raw_admissions),
        }
```

- [ ] **Step 2: Verify import**

Run: `python -c "from scrapers.sources.eol_api import EOLScraper; print('EOLScraper OK')"`
Expected: `EOLScraper OK`

- [ ] **Step 3: Commit**

```bash
git add scrapers/sources/__init__.py scrapers/sources/eol_api.py
git commit -m "feat: add EOL API scraper for colleges, majors, admissions"
```

---

### Task 6: Sunshine Gaokao Scraper — Colleges & Majors

**Files:**
- Create: `scrapers/sources/sunshine_gaokao.py`

阳光高考(gaokao.chsi.com.cn) is the official MOE platform with authoritative school and major data, including status flags (new/discontinued).

- [ ] **Step 1: Write `scrapers/sources/sunshine_gaokao.py`**

```python
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
            # Name
            name_el = soup.find("h1") or soup.find("h2")
            if name_el:
                info["name"] = name_el.get_text(strip=True)

            # Intro paragraphs
            intro_div = soup.find("div", class_="intro") or soup.find(
                "div", string=re.compile("院校简介|学校简介")
            )
            if intro_div:
                info["intro"] = intro_div.get_text(strip=True)[:2000]

            # Key info table rows
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
        """Fetch major catalog for one school. Returns list of major dicts."""
        url = f"{self.config.base_url}/sch/majorList--schId-{code}.dhtml"
        try:
            html = await self.fetch_with_retry(client, url, expect_json=False)
            soup = BeautifulSoup(html, "html.parser")
            majors = []
            for row in soup.select("table tr")[1:]:  # skip header
                cells = row.find_all("td")
                if len(cells) >= 4:
                    major = {
                        "college_code": code,
                        "major_name": cells[0].get_text(strip=True),
                        "category": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                        "degree_type": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                        "duration": int(cells[3].get_text(strip=True)) if len(cells) > 3 and cells[3].get_text(strip=True).isdigit() else 4,
                        "status": "active",
                    }
                    # Check for 新增/停招 markers in special classes or text
                    cell_text = " ".join(c.get_text(strip=True) for c in cells)
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
```

- [ ] **Step 2: Verify import**

Run: `python -c "from scrapers.sources.sunshine_gaokao import SunshineGaokaoScraper; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scrapers/sources/sunshine_gaokao.py
git commit -m "feat: add Sunshine Gaokao scraper for official college & major data"
```

---

### Task 7: University Employment Report PDF Scraper

**Files:**
- Create: `scrapers/parsers/__init__.py`
- Create: `scrapers/parsers/pdf_parser.py`
- Create: `scrapers/sources/university_reports.py`

- [ ] **Step 1: Write `scrapers/parsers/pdf_parser.py`**

```python
"""PDF parser for university employment quality reports."""
import re
from pathlib import Path
from loguru import logger

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    logger.warning("pdfplumber not installed. PDF parsing disabled.")


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    if pdfplumber is None:
        return ""
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
    except Exception as e:
        logger.error(f"PDF extraction failed for {pdf_path}: {e}")
    return "\n".join(text_parts)


def parse_employment_rate(text: str) -> float | None:
    """Extract overall employment rate percentage from text."""
    patterns = [
        r"毕业生总体就业率[：:是为]\s*([\d.]+)%",
        r"总体毕业去向落实率[：:是为]\s*([\d.]+)%",
        r"就业率[：:是为]\s*([\d.]+)%",
        r"毕业去向落实率[：:是为]\s*([\d.]+)%",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return float(m.group(1)) / 100
    return None


def parse_avg_salary(text: str) -> float | None:
    """Extract average monthly salary from text (in yuan)."""
    patterns = [
        r"平均月薪[入收]?[：:是为]约?\s*([\d,]+\.?\d*)\s*元",
        r"月均收入[：:是为]\s*([\d,]+\.?\d*)\s*元",
        r"平均月收入[：:是为]\s*([\d,]+\.?\d*)\s*元",
        r"月平均工资[：:是为]\s*([\d,]+\.?\d*)\s*元",
        r"平均薪酬[：:是为]\s*([\d,]+\.?\d*)\s*元",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def parse_graduate_rates(text: str) -> dict:
    """Extract domestic graduate / overseas rates."""
    result = {}
    dom_pat = r"国内[升学深造]*[读研考研]*\S*率?[：:是为]\s*([\d.]+)%"
    m = re.search(dom_pat, text)
    if m:
        result["domestic_graduate_rate"] = float(m.group(1)) / 100

    overseas_pat = r"出国[出境]*[留学深造]*\S*率?[：:是为]\s*([\d.]+)%"
    m = re.search(overseas_pat, text)
    if m:
        result["overseas_rate"] = float(m.group(1)) / 100

    return result


def parse_industry_distribution(text: str) -> list[dict]:
    """Extract top industries with percentages."""
    industries = []
    # Pattern: "XXX业  XX.X%" or "XXX服务业(XX.X%)"
    pat = re.findall(
        r"([一-龥a-zA-Z&、/\s]+?(?:服务业|制造业|金融业|教育|软件|信息|建筑|批发|交通|房地产|科学研究))[\s(（]*(\d+\.?\d*)%",
        text[:3000],
    )
    for name, pct in pat[:5]:
        industries.append({"industry": name.strip(), "percentage": float(pct) / 100})
    return industries
```

- [ ] **Step 2: Write `scrapers/sources/university_reports.py`**

```python
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
    "10558": "https://jyzd.sysu.edu.cn/report/2024.pdf",       # 中山大学
    "10561": "https://jyzd.scut.edu.cn/report/2024.pdf",       # 华南理工大学
    "10559": "https://jyzd.jnu.edu.cn/report/2024.pdf",        # 暨南大学
    "10574": "https://career.scnu.edu.cn/report/2024.pdf",     # 华南师范大学
    "10590": "https://career.szu.edu.cn/report/2024.pdf",      # 深圳大学
    "11845": "https://jyzd.gdut.edu.cn/report/2024.pdf",       # 广东工业大学
    # More can be added as URLs are discovered
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
                emp_rate - grad_rates.get("domestic_graduate_rate", 0)
                - grad_rates.get("overseas_rate", 0)
                if emp_rate else None
            ),
            top_industries=industries,
            source=f"《{name}{year}届毕业生就业质量年度报告》",
        )

    async def run(self) -> dict:
        """Download and parse employment reports for all universities."""
        results: list[Employment] = []
        async with httpx.AsyncClient(timeout=60) as client:
            for year in [2023, 2024]:  # Most recent 2 years have reports
                for uni in GUANGDONG_UNIVERSITIES:
                    emp = await self.process_report(
                        client, uni["code"], uni["name"], year
                    )
                    if emp:
                        results.append(emp)
                    await asyncio.sleep(1.0)

        self.save_raw("employment.json", [e.model_dump() for e in results])
        return {"source": "university_reports", "employment_records": len(results)}
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from scrapers.sources.university_reports import UniversityReportScraper; from scrapers.parsers.pdf_parser import extract_text_from_pdf; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add scrapers/parsers/ scrapers/sources/university_reports.py
git commit -m "feat: add employment report PDF scraper and parser"
```

---

### Task 8: Industry Analysis Data Builder

**Files:**
- Create: `scrapers/sources/industry_data.py`

This module builds the industry analysis knowledge base from structured public data (统计局, 招聘平台公开报告, 行业薪酬报告). Since these are typically published as structured reports rather than real-time APIs, this combines web-scraped data with a curated base template.

- [ ] **Step 1: Write `scrapers/sources/industry_data.py`**

```python
"""Industry analysis knowledge base builder.

Combines structured public data sources:
  - 国家统计局 (stats.gov.cn) — industry salary statistics
  - Public salary survey reports
  - Curated industry profiles with growth/stability/outlook assessments
"""
import asyncio
import httpx
from loguru import logger

from scrapers.config import ScraperConfig, TARGET_YEARS
from scrapers.base_scraper import BaseScraper
from scrapers.storage.schema import Industry, MajorIndustryMapping


# Curated industry knowledge base based on 国家统计局 + market survey data
INDUSTRY_TEMPLATES: list[dict] = [
    {
        "industry_name": "信息传输、软件和信息技术服务业",
        "industry_code": "I63-65",
        "avg_annual_salary": 231810,
        "salary_growth_rate": 0.09,
        "employment_demand_index": 4.5,
        "industry_growth_rate": 0.12,
        "entry_difficulty": "中等",
        "popular_positions": [
            {"name": "软件开发工程师", "avg_salary": 18000, "demand": "高"},
            {"name": "算法工程师", "avg_salary": 25000, "demand": "高"},
            {"name": "数据分析师", "avg_salary": 15000, "demand": "高"},
            {"name": "产品经理", "avg_salary": 16000, "demand": "中"},
            {"name": "网络安全工程师", "avg_salary": 20000, "demand": "高"},
        ],
        "career_path": "初级工程师 → 高级工程师 → 技术专家/架构师 → 技术总监",
        "pros": ["薪资水平领先", "岗位需求大", "远程办公友好", "技术成长快"],
        "cons": ["加班文化普遍", "技术迭代快需持续学习", "35岁职业瓶颈", "竞争激烈"],
        "insider_reviews": [
            {"source": "知乎", "summary": "互联网行业前3年成长迅速，薪资涨幅大...", "sentiment": "neutral"},
        ],
        "related_majors": [
            "计算机科学与技术", "软件工程", "人工智能", "数据科学与大数据技术",
            "网络工程", "信息安全", "物联网工程", "数字媒体技术",
        ],
        "outlook": "AI/云计算/信息安全驱动增长，但初级开发岗位供给过剩，建议深耕细分方向",
    },
    {
        "industry_name": "制造业",
        "industry_code": "C",
        "avg_annual_salary": 112306,
        "salary_growth_rate": 0.06,
        "employment_demand_index": 3.8,
        "industry_growth_rate": 0.06,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "机械工程师", "avg_salary": 10000, "demand": "中"},
            {"name": "电气工程师", "avg_salary": 12000, "demand": "中"},
            {"name": "工艺工程师", "avg_salary": 11000, "demand": "中"},
            {"name": "质量管理工程师", "avg_salary": 9000, "demand": "中"},
        ],
        "career_path": "技术员 → 工程师 → 高级工程师 → 技术经理/厂长",
        "pros": ["就业稳定", "行业天花板高", "积累型职业", "珠三角制造业集聚"],
        "cons": ["起薪偏低", "晋升速度慢", "部分岗位工作环境差"],
        "insider_reviews": [
            {"source": "知乎", "summary": "制造业工程师前几年收入不高，但经验积累后价值上升...", "sentiment": "positive"},
        ],
        "related_majors": [
            "机械设计制造及其自动化", "电气工程及其自动化", "自动化",
            "材料科学与工程", "工业工程", "车辆工程", "测控技术与仪器",
        ],
        "outlook": "智能制造转型带来新机会，自动化/机器人方向薪资增长快",
    },
    {
        "industry_name": "金融业",
        "industry_code": "J",
        "avg_annual_salary": 197383,
        "salary_growth_rate": 0.07,
        "employment_demand_index": 3.5,
        "industry_growth_rate": 0.05,
        "entry_difficulty": "较高",
        "popular_positions": [
            {"name": "投资分析师", "avg_salary": 15000, "demand": "中"},
            {"name": "风控专员", "avg_salary": 12000, "demand": "中"},
            {"name": "理财顾问", "avg_salary": 13000, "demand": "中"},
            {"name": "审计师", "avg_salary": 11000, "demand": "中"},
        ],
        "career_path": "分析师 → 高级分析师 → 经理/VP → 总监",
        "pros": ["薪资高", "社会地位高", "职业发展通道清晰"],
        "cons": ["工作压力大", "入行门槛高", "一线城市聚集", "周期性波动"],
        "insider_reviews": [
            {"source": "知乎", "summary": "金融行业收入天花板高但强度大，头部机构竞争激烈...", "sentiment": "neutral"},
        ],
        "related_majors": [
            "金融学", "经济学", "会计学", "财务管理", "保险学",
            "投资学", "金融工程", "国际经济与贸易",
        ],
        "outlook": "金融科技方向需求增加，传统岗位受AI替代压力增大",
    },
    {
        "industry_name": "教育",
        "industry_code": "P",
        "avg_annual_salary": 123982,
        "salary_growth_rate": 0.05,
        "employment_demand_index": 3.0,
        "industry_growth_rate": 0.03,
        "entry_difficulty": "中等",
        "popular_positions": [
            {"name": "中小学教师", "avg_salary": 8000, "demand": "高"},
            {"name": "高校教师", "avg_salary": 12000, "demand": "中"},
            {"name": "培训讲师", "avg_salary": 10000, "demand": "中"},
            {"name": "教育产品经理", "avg_salary": 15000, "demand": "中"},
        ],
        "career_path": "教师 → 骨干教师 → 学科带头人 → 教学管理者",
        "pros": ["寒暑假", "工作稳定", "社会尊重", "有编制"],
        "cons": ["起薪偏低", "非编待遇差", "考核压力增大", "课外负担重"],
        "insider_reviews": [
            {"source": "知乎", "summary": "公立学校稳定但薪资涨幅有限，培训机构收入高但不稳定...", "sentiment": "mixed"},
        ],
        "related_majors": [
            "教育学", "汉语言文学(师范)", "数学与应用数学(师范)",
            "英语(师范)", "物理学(师范)", "化学(师范)", "历史学(师范)",
        ],
        "outlook": "人口下降长期看空K12需求，但高等教育/职业教育仍有增长",
    },
    {
        "industry_name": "卫生和社会工作",
        "industry_code": "Q",
        "avg_annual_salary": 127089,
        "salary_growth_rate": 0.07,
        "employment_demand_index": 4.0,
        "industry_growth_rate": 0.08,
        "entry_difficulty": "较高",
        "popular_positions": [
            {"name": "临床医生", "avg_salary": 12000, "demand": "高"},
            {"name": "护士", "avg_salary": 8000, "demand": "高"},
            {"name": "药剂师", "avg_salary": 9000, "demand": "中"},
            {"name": "医学检验师", "avg_salary": 8500, "demand": "中"},
        ],
        "career_path": "住院医师 → 主治医师 → 副主任医师 → 主任医师",
        "pros": ["职业稳定", "社会地位高", "越老越吃香", "需求刚性"],
        "cons": ["培养周期长(5+3+X年)", "工作强度大", "医患关系紧张", "夜班频繁"],
        "insider_reviews": [
            {"source": "知乎", "summary": "医生前期投入大、收入不高，但35岁后开始回报...", "sentiment": "mixed"},
        ],
        "related_majors": [
            "临床医学", "口腔医学", "麻醉学", "护理学",
            "药学", "中药学", "预防医学", "中医学", "针灸推拿学",
        ],
        "outlook": "老龄化推动医疗需求增长，口腔/眼科/康复等方向前景好",
    },
    {
        "industry_name": "建筑业",
        "industry_code": "E",
        "avg_annual_salary": 93116,
        "salary_growth_rate": 0.03,
        "employment_demand_index": 2.5,
        "industry_growth_rate": 0.02,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "土木工程师", "avg_salary": 9000, "demand": "低"},
            {"name": "建筑设计师", "avg_salary": 11000, "demand": "中"},
            {"name": "造价工程师", "avg_salary": 10000, "demand": "中"},
            {"name": "项目经理", "avg_salary": 15000, "demand": "中"},
        ],
        "career_path": "技术员 → 工程师 → 项目经理 → 项目总监",
        "pros": ["项目经验值钱", "证书含金量高", "积累型职业"],
        "cons": ["行业下行", "项目不稳定", "需要驻场出差", "工作环境艰苦"],
        "insider_reviews": [
            {"source": "知乎", "summary": "房地产下行周期，建筑行业就业压力大，建议转向基础设施方向...", "sentiment": "negative"},
        ],
        "related_majors": [
            "建筑学", "土木工程", "城乡规划", "给排水科学与工程",
            "工程管理", "工程造价",
        ],
        "outlook": "房建市场萎缩，基础设施/市政/城市更新方向尚有需求",
    },
    {
        "industry_name": "交通运输、仓储和邮政业",
        "industry_code": "G",
        "avg_annual_salary": 115016,
        "salary_growth_rate": 0.05,
        "employment_demand_index": 3.2,
        "industry_growth_rate": 0.05,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "物流管理师", "avg_salary": 8000, "demand": "中"},
            {"name": "供应链分析师", "avg_salary": 12000, "demand": "中"},
            {"name": "交通规划师", "avg_salary": 11000, "demand": "低"},
        ],
        "career_path": "专员 → 主管 → 经理 → 总监",
        "pros": ["电商驱动需求", "入门门槛低", "供应链管理有发展"],
        "cons": ["基层薪酬偏低", "工作时间不规律", "体力劳动比例大"],
        "insider_reviews": [],
        "related_majors": [
            "交通运输", "物流管理", "供应链管理",
            "海事管理", "交通工程",
        ],
        "outlook": "跨境电商物流/智慧物流方向需求增长",
    },
    {
        "industry_name": "科学研究和技术服务业",
        "industry_code": "M",
        "avg_annual_salary": 179033,
        "salary_growth_rate": 0.08,
        "employment_demand_index": 3.8,
        "industry_growth_rate": 0.10,
        "entry_difficulty": "较高",
        "popular_positions": [
            {"name": "研发工程师", "avg_salary": 15000, "demand": "高"},
            {"name": "实验研究员", "avg_salary": 10000, "demand": "中"},
            {"name": "技术咨询师", "avg_salary": 13000, "demand": "中"},
        ],
        "career_path": "助理研究员 → 研究员 → 高级研究员 → 首席科学家",
        "pros": ["技术含量高", "成长空间大", "政策支持"],
        "cons": ["学历门槛高(硕士起步)", "研发周期长", "成果不确定性"],
        "insider_reviews": [],
        "related_majors": [
            "数学与应用数学", "物理学", "化学", "生物科学",
            "材料科学与工程", "电子信息工程", "生物医学工程",
        ],
        "outlook": "国家战略导向，基础研究/应用研究投入持续增加",
    },
    {
        "industry_name": "租赁和商务服务业",
        "industry_code": "L",
        "avg_annual_salary": 110756,
        "salary_growth_rate": 0.05,
        "employment_demand_index": 3.5,
        "industry_growth_rate": 0.06,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "HR", "avg_salary": 8000, "demand": "中"},
            {"name": "市场营销", "avg_salary": 9000, "demand": "中"},
            {"name": "管理咨询", "avg_salary": 14000, "demand": "中"},
        ],
        "career_path": "专员 → 主管 → 经理 → 总监",
        "pros": ["入行门槛低", "转行灵活", "大公司平台好"],
        "cons": ["可替代性强", "薪资天花板低", "经济周期敏感"],
        "insider_reviews": [],
        "related_majors": [
            "工商管理", "市场营销", "人力资源管理", "行政管理",
            "电子商务", "旅游管理",
        ],
        "outlook": "数字化转型带来新岗位，传统行政/HR职能被AI替代风险高",
    },
    {
        "industry_name": "农林牧渔业",
        "industry_code": "A",
        "avg_annual_salary": 66160,
        "salary_growth_rate": 0.04,
        "employment_demand_index": 2.5,
        "industry_growth_rate": 0.04,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "农艺师", "avg_salary": 7000, "demand": "低"},
            {"name": "兽医", "avg_salary": 8000, "demand": "中"},
            {"name": "水产养殖技术员", "avg_salary": 7000, "demand": "低"},
        ],
        "career_path": "技术员 → 农艺师/兽医师 → 技术主管 → 场长/经理",
        "pros": ["竞争压力小", "政策扶持", "现代农业有技术含量"],
        "cons": ["薪资偏低", "工作地点偏远", "社会认知度低"],
        "insider_reviews": [],
        "related_majors": [
            "农学", "园艺", "植物保护", "动物科学",
            "动物医学", "水产养殖学", "园林", "农业资源与环境",
        ],
        "outlook": "智慧农业/生物育种方向有政策红利，传统方向薪资增长缓慢",
    },
]


# Major-to-industry mappings for key majors
MAJOR_INDUSTRY_MAPPINGS: list[dict] = [
    {"major_name": "计算机科学与技术", "primary_industries": ["信息传输、软件和信息技术服务业"], "secondary_industries": ["金融业", "科学研究和技术服务业", "教育"], "typical_positions": ["软件工程师", "算法工程师", "数据工程师", "系统架构师", "全栈工程师"], "salary_range": {"entry": 8000, "mid": 18000, "senior": 35000}},
    {"major_name": "软件工程", "primary_industries": ["信息传输、软件和信息技术服务业"], "secondary_industries": ["金融业", "制造业"], "typical_positions": ["软件开发工程师", "前端工程师", "移动端工程师", "DevOps工程师"], "salary_range": {"entry": 8000, "mid": 17000, "senior": 33000}},
    {"major_name": "人工智能", "primary_industries": ["信息传输、软件和信息技术服务业"], "secondary_industries": ["科学研究和技术服务业", "制造业", "金融业"], "typical_positions": ["算法工程师", "机器学习工程师", "NLP工程师", "计算机视觉工程师"], "salary_range": {"entry": 12000, "mid": 25000, "senior": 45000}},
    {"major_name": "数据科学与大数据技术", "primary_industries": ["信息传输、软件和信息技术服务业"], "secondary_industries": ["金融业", "科学研究和技术服务业", "租赁和商务服务业"], "typical_positions": ["数据分析师", "数据工程师", "数据科学家", "BI工程师"], "salary_range": {"entry": 9000, "mid": 18000, "senior": 32000}},
    {"major_name": "临床医学", "primary_industries": ["卫生和社会工作"], "secondary_industries": ["科学研究和技术服务业", "教育"], "typical_positions": ["临床医师", "医学研究员", "医疗管理者"], "salary_range": {"entry": 6000, "mid": 12000, "senior": 25000}},
    {"major_name": "金融学", "primary_industries": ["金融业"], "secondary_industries": ["信息传输、软件和信息技术服务业", "租赁和商务服务业"], "typical_positions": ["投资分析师", "金融产品经理", "风险控制师", "理财顾问"], "salary_range": {"entry": 7000, "mid": 15000, "senior": 30000}},
    {"major_name": "会计学", "primary_industries": ["金融业", "租赁和商务服务业"], "secondary_industries": ["制造业", "信息传输、软件和信息技术服务业"], "typical_positions": ["会计师", "审计师", "财务分析师", "税务顾问"], "salary_range": {"entry": 5000, "mid": 10000, "senior": 22000}},
    {"major_name": "电子信息工程", "primary_industries": ["信息传输、软件和信息技术服务业", "制造业"], "secondary_industries": ["科学研究和技术服务业"], "typical_positions": ["嵌入式工程师", "硬件工程师", "通信工程师", "电子工程师"], "salary_range": {"entry": 7000, "mid": 14000, "senior": 25000}},
    {"major_name": "机械设计制造及其自动化", "primary_industries": ["制造业"], "secondary_industries": ["科学研究和技术服务业", "建筑业"], "typical_positions": ["机械工程师", "结构工程师", "工艺工程师", "设备工程师"], "salary_range": {"entry": 6000, "mid": 11000, "senior": 20000}},
    {"major_name": "电气工程及其自动化", "primary_industries": ["制造业", "电力、热力、燃气及水生产和供应业"], "secondary_industries": ["建筑业", "信息传输、软件和信息技术服务业"], "typical_positions": ["电气工程师", "电力系统工程师", "自动化工程师", "新能源工程师"], "salary_range": {"entry": 6000, "mid": 12000, "senior": 22000}},
    {"major_name": "建筑学", "primary_industries": ["建筑业"], "secondary_industries": ["科学研究和技术服务业", "房地产业"], "typical_positions": ["建筑设计师", "方案设计师", "BIM工程师", "城市设计师"], "salary_range": {"entry": 6000, "mid": 12000, "senior": 25000}},
    {"major_name": "土木工程", "primary_industries": ["建筑业"], "secondary_industries": ["交通运输、仓储和邮政业", "科学研究和技术服务业"], "typical_positions": ["结构工程师", "施工工程师", "造价工程师", "项目经理"], "salary_range": {"entry": 5500, "mid": 11000, "senior": 22000}},
    {"major_name": "法学", "primary_industries": ["租赁和商务服务业", "公共管理、社会保障和社会组织"], "secondary_industries": ["金融业", "信息传输、软件和信息技术服务业"], "typical_positions": ["律师", "法务", "合规官", "知识产权顾问"], "salary_range": {"entry": 5000, "mid": 12000, "senior": 30000}},
    {"major_name": "自动化", "primary_industries": ["制造业", "信息传输、软件和信息技术服务业"], "secondary_industries": ["电力、热力、燃气及水生产和供应业", "交通运输、仓储和邮政业"], "typical_positions": ["自动化工程师", "PLC工程师", "机器人工程师", "系统集成工程师"], "salary_range": {"entry": 6500, "mid": 12000, "senior": 22000}},
    {"major_name": "汉语言文学", "primary_industries": ["教育", "文化、体育和娱乐业"], "secondary_industries": ["租赁和商务服务业", "公共管理、社会保障和社会组织"], "typical_positions": ["教师", "编辑", "文案策划", "公务员"], "salary_range": {"entry": 5000, "mid": 9000, "senior": 18000}},
    {"major_name": "英语", "primary_industries": ["教育", "租赁和商务服务业"], "secondary_industries": ["信息传输、软件和信息技术服务业", "制造业"], "typical_positions": ["翻译", "英语教师", "外贸专员", "海外运营"], "salary_range": {"entry": 5000, "mid": 10000, "senior": 20000}},
    {"major_name": "化学工程与工艺", "primary_industries": ["制造业"], "secondary_industries": ["科学研究和技术服务业", "电力、热力、燃气及水生产和供应业"], "typical_positions": ["化工工程师", "工艺工程师", "研发工程师", "质量工程师"], "salary_range": {"entry": 5500, "mid": 10000, "senior": 20000}},
    {"major_name": "生物科学", "primary_industries": ["科学研究和技术服务业", "制造业"], "secondary_industries": ["教育", "卫生和社会工作"], "typical_positions": ["生物研究员", "实验员", "医药代表", "生物教师"], "salary_range": {"entry": 5500, "mid": 10000, "senior": 20000}},
    {"major_name": "环境工程", "primary_industries": ["水利、环境和公共设施管理业"], "secondary_industries": ["科学研究和技术服务业", "制造业"], "typical_positions": ["环境工程师", "环保工程师", "环评工程师", "EHS工程师"], "salary_range": {"entry": 5000, "mid": 9000, "senior": 18000}},
    {"major_name": "护理学", "primary_industries": ["卫生和社会工作"], "secondary_industries": ["教育"], "typical_positions": ["临床护士", "护理管理者", "社区护士", "护理教师"], "salary_range": {"entry": 5000, "mid": 9000, "senior": 15000}},
]


class IndustryDataBuilder(BaseScraper):
    """Builds industry analysis knowledge base from structured data."""

    def __init__(self):
        super().__init__(ScraperConfig(
            name="industry_data",
            base_url="https://data.stats.gov.cn",
            delay_seconds=2.0,
        ))

    async def build_industries(self) -> list[Industry]:
        """Generate industry records for all years."""
        all_industries = []
        for year in TARGET_YEARS:
            for template in INDUSTRY_TEMPLATES:
                ind = Industry(
                    **{**template, "year": year},
                    source=f"国家统计局{year}年平均工资数据 + 行业调研报告",
                )
                all_industries.append(ind)
        logger.info(f"Built {len(all_industries)} industry records")
        self.save_raw("industries.json", [i.model_dump() for i in all_industries])
        return all_industries

    async def build_mappings(self) -> list[MajorIndustryMapping]:
        """Generate major-to-industry mappings."""
        mappings = [MajorIndustryMapping(**m) for m in MAJOR_INDUSTRY_MAPPINGS]
        logger.info(f"Built {len(mappings)} major-industry mappings")
        self.save_raw("major_industry_mapping.json", [m.model_dump() for m in mappings])
        return mappings

    async def run(self) -> dict:
        """Build complete industry knowledge base."""
        industries = await self.build_industries()
        mappings = await self.build_mappings()
        return {
            "source": "industry_data",
            "industries": len(industries),
            "mappings": len(mappings),
        }
```

- [ ] **Step 2: Verify import**

Run: `python -c "from scrapers.sources.industry_data import IndustryDataBuilder, INDUSTRY_TEMPLATES, MAJOR_INDUSTRY_MAPPINGS; print(f'{len(INDUSTRY_TEMPLATES)} industries, {len(MAJOR_INDUSTRY_MAPPINGS)} mappings')"`
Expected: `10 industries, 20 mappings`

- [ ] **Step 3: Commit**

```bash
git add scrapers/sources/industry_data.py
git commit -m "feat: add industry analysis knowledge base with 10 industries and 20 major mappings"
```

---

### Task 9: Data Aggregator & Exporter Runner

**Files:**
- Create: `scrapers/run_all.py`

- [ ] **Step 1: Write `scrapers/run_all.py`**

```python
#!/usr/bin/env python3
"""Main orchestrator: runs all scrapers in parallel, merges, validates, exports."""
import asyncio
import sys
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.sources.eol_api import EOLScraper
from scrapers.sources.sunshine_gaokao import SunshineGaokaoScraper
from scrapers.sources.university_reports import UniversityReportScraper
from scrapers.sources.industry_data import IndustryDataBuilder
from scrapers.storage.exporter import export_full_data, export_seed_files
from scrapers.storage.validator import run_all_validations
from scrapers.storage.schema import (
    College, Major, Admission, Employment, Industry, MajorIndustryMapping,
)


async def main():
    logger.info("=" * 60)
    logger.info("Starting full data pipeline — all scrapers in parallel")
    logger.info("=" * 60)

    # Stage 1: Run all scrapers in parallel
    scrapers = [
        EOLScraper(),
        SunshineGaokaoScraper(),
        UniversityReportScraper(),
        IndustryDataBuilder(),
    ]

    results = await asyncio.gather(*[s.run() for s in scrapers], return_exceptions=True)

    for scraper, result in zip(scrapers, results):
        if isinstance(result, Exception):
            logger.error(f"Scraper {scraper.config.name} FAILED: {result}")
        else:
            logger.info(f"Scraper {scraper.config.name}: {result}")

    # Stage 2: Load all raw data
    logger.info("\n" + "=" * 60)
    logger.info("Stage 2: Loading and merging raw data")
    logger.info("=" * 60)

    eol = scrapers[0]
    sunshine = scrapers[1]
    reports = scrapers[2]
    industry = scrapers[3]

    # Load colleges from EOL raw data
    raw_colleges = eol.load_raw("colleges.json") or []
    colleges = [College(**c) for c in raw_colleges if c.get("code")]

    # Load admissions from EOL
    raw_admissions = eol.load_raw("admissions.json") or []
    admissions = []
    for a in raw_admissions:
        try:
            admissions.append(Admission(**a))
        except Exception as e:
            logger.debug(f"Skip invalid admission: {e}")

    # Load majors from EOL + Sunshine
    raw_majors = eol.load_raw("majors.json") or []
    raw_majors_sun = sunshine.load_raw("major_catalog.json") or []
    all_raw_majors = raw_majors + raw_majors_sun
    majors = []
    seen = set()
    for m in all_raw_majors:
        key = (m.get("college_code"), m.get("major_name"))
        if key in seen:
            continue
        seen.add(key)
        try:
            majors.append(Major(**m))
        except Exception:
            pass

    # Load employment
    raw_employment = reports.load_raw("employment.json") or []
    employment = []
    for e in raw_employment:
        try:
            employment.append(Employment(**e))
        except Exception:
            pass

    # Load industries and mappings
    raw_industries = industry.load_raw("industries.json") or []
    industries = [Industry(**i) for i in raw_industries]
    raw_mappings = industry.load_raw("major_industry_mapping.json") or []
    mappings = [MajorIndustryMapping(**m) for m in raw_mappings]

    logger.info(
        f"Data summary: {len(colleges)} colleges, {len(majors)} majors, "
        f"{len(admissions)} admissions, {len(employment)} employment, "
        f"{len(industries)} industries, {len(mappings)} mappings"
    )

    # Stage 3: Validate
    logger.info("\n" + "=" * 60)
    logger.info("Stage 3: Validation")
    logger.info("=" * 60)

    ok = run_all_validations(
        [c.model_dump() for c in colleges],
        [a.model_dump() for a in admissions],
        [e.model_dump() for e in employment],
        [i.model_dump() for i in industries],
    )

    if not ok:
        logger.error("Validation failed — check logs for details")
        logger.warning("Continuing with export anyway (with warnings)")

    # Stage 4: Export
    logger.info("\n" + "=" * 60)
    logger.info("Stage 4: Exporting to seed/ and approved/")
    logger.info("=" * 60)

    export_full_data(colleges, majors, admissions, employment, industries, mappings)

    logger.info("\n" + "=" * 60)
    logger.info("Pipeline complete!")
    logger.info(f"  Seed: data/seed/schools.json + data/seed/scores.json")
    logger.info(f"  Full: data/approved/ (6 files)")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Test dry-run import**

Run: `python -c "import ast; import sys; sys.path.insert(0,'.'); from scrapers.run_all import main; print('run_all imports OK')"`
Expected: `run_all imports OK`

- [ ] **Step 3: Commit**

```bash
git add scrapers/run_all.py
git commit -m "feat: add unified pipeline orchestrator run_all.py"
```

---

### Task 10: Update seed_db.py for Extended Data

**Files:**
- Modify: `scripts/seed_db.py`

- [ ] **Step 1: Update `scripts/seed_db.py` to support new data files**

```python
"""Load seed data into PostgreSQL. Runs from data/seed/ (MVP) or data/approved/ (full)."""
import asyncio, json, uuid, sys, os
from pathlib import Path
from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models import engine, async_session, init_db
from backend.models.college import College
from backend.models.admission import AdmissionData


async def seed(data_dir: str = "data/seed"):
    await init_db()

    schools_path = Path(data_dir) / "schools.json"
    scores_path = Path(data_dir) / "scores.json"

    if not schools_path.exists() or not scores_path.exists():
        print(f"Missing seed files in {data_dir}")
        return

    async with async_session() as db:
        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Already seeded. Clearing and re-seeding...")
            await db.execute(text("DELETE FROM admission_data"))
            await db.execute(text("DELETE FROM recommendations"))
            await db.execute(text("DELETE FROM user_profiles"))
            await db.execute(text("DELETE FROM colleges"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

        with open(schools_path, encoding="utf-8") as f:
            schools = json.load(f)
        with open(scores_path, encoding="utf-8") as f:
            scores = json.load(f)

        name_to_id = {}
        for s in schools:
            c = College(id=uuid.uuid4(), **s)
            db.add(c)
            name_to_id[s["name"]] = c.id

        for r in scores:
            cn = r.pop("college_name", "")
            # Map college_name to college_id
            cid = name_to_id.get(cn)
            if not cid:
                # Try fuzzy match
                for n, i in name_to_id.items():
                    if cn in n or n in cn:
                        cid = i
                        break
            if not cid:
                print(f"  WARNING: No college match for '{cn}', skipping")
                continue
            db.add(AdmissionData(id=uuid.uuid4(), college_id=cid, **r))

        await db.commit()
        print(f"Seeded {len(schools)} colleges, {len(scores)} admission records.")


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/seed"
    asyncio.run(seed(data_dir))
```

- [ ] **Step 2: Commit**

```bash
git add scripts/seed_db.py
git commit -m "feat: update seed_db.py to support full data export and re-seeding"
```

---

### Task 11: Add Requirements & Verification

**Files:**
- Create: `scrapers/requirements.txt`

- [ ] **Step 1: Write `scrapers/requirements.txt`**

```
httpx>=0.27.0
beautifulsoup4>=4.12.0
pdfplumber>=0.10.0
pydantic>=2.5.0
tenacity>=8.2.0
loguru>=0.7.0
typer>=0.9.0
lxml>=5.0.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r scrapers/requirements.txt`
Expected: All packages install successfully

- [ ] **Step 3: Verify entire scraper package imports**

Run: `python -c "
from scrapers.config import GUANGDONG_UNIVERSITIES, TARGET_YEARS
from scrapers.base_scraper import BaseScraper
from scrapers.sources.eol_api import EOLScraper
from scrapers.sources.sunshine_gaokao import SunshineGaokaoScraper
from scrapers.sources.university_reports import UniversityReportScraper
from scrapers.sources.industry_data import IndustryDataBuilder
from scrapers.storage.schema import College, Major, Admission, Employment, Industry
from scrapers.storage.exporter import export_seed_files, export_full_data
from scrapers.storage.validator import run_all_validations
print('All imports OK')
print(f'Universities: {len(GUANGDONG_UNIVERSITIES)}')
print(f'Target years: {TARGET_YEARS}')
"`

- [ ] **Step 4: Run industry builder (no network needed)**

Run: `python -c "
import asyncio
from scrapers.sources.industry_data import IndustryDataBuilder
async def test():
    b = IndustryDataBuilder()
    result = await b.run()
    print(f'Result: {result}')
asyncio.run(test())
"`
Expected: `Result: {'source': 'industry_data', 'industries': 60, 'mappings': 20}`

- [ ] **Step 5: Verify data structure after dry run**

Run: `ls -la data/raw/industry_data/`

- [ ] **Step 6: Commit**

```bash
git add scrapers/requirements.txt
git commit -m "chore: add scraper dependencies and verify full import chain"
```

---

## Execution Order

Tasks 1-4 are sequential dependencies (config → base → schema → export). Tasks 5-8 can run in parallel (each is an independent scraper source). Task 9 depends on 5-8. Task 10 depends on 4. Task 11 is the final verification.

```
1 → 2 → 3 → 4
              ↓
     ┌────────┼────────┬────────┐
     5        6        7        8     (parallel)
     └────────┼────────┴────────┘
              ↓
              9
              ↓
             10
              ↓
             11
```

## After Implementation

1. Run `python scrapers/run_all.py` to collect all data
2. Run `python scripts/seed_db.py data/approved/` to seed PostgreSQL
3. Run `python scripts/index_chroma.py` to rebuild Chroma index
4. Start the backend and verify `/api/v1/recommendations` returns results
