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
    # Build schools.json in the existing seed format
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
