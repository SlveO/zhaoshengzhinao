#!/usr/bin/env python3
"""Main orchestrator: runs all scrapers in parallel, merges, validates, exports.

Data sources:
  - GaokaoScoreScraper: admission scores + college info (working API)
  - UniversityReportScraper: employment reports (URLs need updating)
  - IndustryDataBuilder: industry knowledge base (no network needed)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from scrapers.sources.eol_api import GaokaoScoreScraper, SCHOOL_ID_MAP
from scrapers.sources.university_reports import UniversityReportScraper
from scrapers.sources.industry_data import IndustryDataBuilder
from scrapers.storage.exporter import export_full_data, export_seed_files
from scrapers.storage.validator import run_all_validations
from scrapers.storage.schema import (
    College, Major, Admission, Employment, Industry, MajorIndustryMapping,
)
from scrapers.config import GUANGDONG_UNIVERSITIES


async def main():
    logger.info("=" * 60)
    logger.info("Starting full data pipeline — all scrapers in parallel")
    logger.info("=" * 60)

    # Stage 1: Run all scrapers in parallel
    scrapers = [
        GaokaoScoreScraper(),
        UniversityReportScraper(),
        IndustryDataBuilder(),
    ]

    results = await asyncio.gather(
        *[s.run() for s in scrapers], return_exceptions=True
    )

    for scraper, result in zip(scrapers, results):
        if isinstance(result, Exception):
            logger.error(
                f"Scraper {scraper.config.name} FAILED: {result}"
            )
        else:
            logger.info(f"Scraper {scraper.config.name}: {result}")

    # Stage 2: Load all raw data
    logger.info("\n" + "=" * 60)
    logger.info("Stage 2: Loading and merging raw data")
    logger.info("=" * 60)

    scores_scraper = scrapers[0]
    reports = scrapers[1]
    industry = scrapers[2]

    colleges, majors, admissions = [], [], []
    employment, industries, mappings = [], [], []

    # Build platform_id -> moe_code lookup
    pid_to_code: dict[int, str] = {
        pid: code for code, pid in SCHOOL_ID_MAP.items() if pid > 0
    }
    code_to_pid: dict[str, int] = {
        code: pid for code, pid in SCHOOL_ID_MAP.items() if pid > 0
    }

    try:
        # Load colleges from gaokao_score scraper
        raw_colleges = scores_scraper.load_raw("colleges.json") or []
        platform_to_code = {}  # str(platform_id) -> moe_code
        for c in raw_colleges:
            moe_code = c.get("moe_code", "")
            pid = c.get("platform_id", "")
            if pid:
                platform_to_code[str(pid)] = moe_code
            try:
                college = College(
                    code=moe_code or "",
                    name=c.get("name", ""),
                    type=c.get("type", "综合"),
                    level=c.get("level", "省重点"),
                    province="广东",
                    city=c.get("city", ""),
                    is_985=c.get("is_985", False),
                    is_211=c.get("is_211", False),
                    is_double_first=c.get("is_double_first", False),
                    intro=c.get("intro", ""),
                    website=c.get("website", ""),
                )
                colleges.append(college)
            except Exception as e:
                logger.warning(
                    f"Skip invalid college "
                    f"{c.get('name','?')}: {e}"
                )

        # Supplement: add any config universities not found in API data
        api_codes = {c.code for c in colleges}
        for uni in GUANGDONG_UNIVERSITIES:
            if uni["code"] not in api_codes:
                try:
                    colleges.append(College(**{
                        **uni,
                        "is_985": uni.get("level") == "985",
                        "is_211": uni.get("level") in ("985", "211"),
                        "is_double_first": uni.get("level")
                        in ("985", "211", "双一流"),
                        "intro": "",
                    }))
                except Exception:
                    pass

        # Load admissions from gaokao_score scraper
        raw_admissions = scores_scraper.load_raw("admissions.json") or []
        skipped_platform = 0
        for a in raw_admissions:
            pid = a.get("platform_id", "")
            college_code = platform_to_code.get(str(pid), "")
            if not college_code:
                skipped_platform += 1
                continue
            try:
                admissions.append(Admission(
                    college_code=college_code,
                    major_name=a.get("major_name", ""),
                    major_group=a.get("major_group", ""),
                    year=a.get("year", 2024),
                    province="广东",
                    batch=a.get("batch", "本科批"),
                    subject_requirements=a.get("subject_requirements", ""),
                    plan_count=a.get("plan_count"),
                    min_score=a.get("min_score") or 0,
                    min_rank=a.get("min_rank"),
                    avg_score=a.get("avg_score"),
                    max_score=a.get("max_score"),
                    source_url=a.get("source_url", ""),
                ))
            except Exception as e:
                logger.warning(f"Skip invalid admission: {e}")
        if skipped_platform:
            logger.warning(
                f"Skipped {skipped_platform} admissions: "
                f"unknown platform_id"
            )

        # Build majors from admission data (deduplicate by college_code + major_name)
        seen_majors = set()
        for a in admissions:
            key = (a.college_code, a.major_name)
            if key not in seen_majors:
                seen_majors.add(key)
                try:
                    majors.append(Major(
                        college_code=a.college_code,
                        major_name=a.major_name,
                        major_code="",
                        category="",
                        status="active",
                    ))
                except Exception:
                    pass

        # Load employment
        raw_employment = reports.load_raw("employment.json") or []
        for e in raw_employment:
            try:
                employment.append(Employment(**e))
            except Exception:
                pass

        # Load industries and mappings
        raw_industries = industry.load_raw("industries.json") or []
        for i in raw_industries:
            try:
                industries.append(Industry(**i))
            except Exception as e:
                logger.warning(f"Skip invalid industry: {e}")

        raw_mappings = (
            industry.load_raw("major_industry_mapping.json") or []
        )
        for m in raw_mappings:
            try:
                mappings.append(MajorIndustryMapping(**m))
            except Exception as e:
                logger.warning(f"Skip invalid mapping: {e}")

        logger.info(
            f"Data summary: {len(colleges)} colleges, "
            f"{len(majors)} majors, {len(admissions)} admissions, "
            f"{len(employment)} employment, {len(industries)} industries, "
            f"{len(mappings)} mappings"
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

        export_full_data(
            colleges, majors, admissions,
            employment, industries, mappings
        )

        logger.info("\n" + "=" * 60)
        logger.info("Pipeline complete!")
        logger.info(
            f"  Seed: data/seed/schools.json ({len(colleges)} schools) "
            f"+ data/seed/scores.json ({len(admissions)} scores)"
        )
        logger.info("  Full: data/approved/ (6 files)")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline crashed: {e}", exc_info=True)
    finally:
        for s in scrapers:
            await s.close()


if __name__ == "__main__":
    asyncio.run(main())
