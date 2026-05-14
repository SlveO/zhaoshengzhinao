#!/usr/bin/env python3
"""Main orchestrator: runs all scrapers in parallel, merges, validates, exports."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

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

    eol = scrapers[0]
    sunshine = scrapers[1]
    reports = scrapers[2]
    industry = scrapers[3]

    colleges, majors, admissions = [], [], []
    employment, industries, mappings = [], [], []

    try:
        # Load colleges from EOL raw data
        raw_colleges = eol.load_raw("colleges.json") or []
        for c in raw_colleges:
            if not c.get("code"):
                continue
            try:
                colleges.append(College(**c))
            except Exception as e:
                logger.warning(f"Skip invalid college {c.get('name','?')}: {e}")

        # Load admissions from EOL
        raw_admissions = eol.load_raw("admissions.json") or []
        for a in raw_admissions:
            try:
                admissions.append(Admission(**a))
            except Exception as e:
                logger.warning(f"Skip invalid admission: {e}")

        # Load majors from EOL + Sunshine
        raw_majors = eol.load_raw("majors.json") or []
        raw_majors_sun = sunshine.load_raw("major_catalog.json") or []
        all_raw_majors = raw_majors + raw_majors_sun
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
            colleges, majors, admissions, employment, industries, mappings
        )

        logger.info("\n" + "=" * 60)
        logger.info("Pipeline complete!")
        logger.info("  Seed: data/seed/schools.json + data/seed/scores.json")
        logger.info("  Full: data/approved/ (6 files)")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline crashed: {e}", exc_info=True)
    finally:
        # Always clean up scrapers to release log handlers
        for s in scrapers:
            await s.close()


if __name__ == "__main__":
    asyncio.run(main())
