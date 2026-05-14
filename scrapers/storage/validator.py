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
        score = item.get("min_score")
        if score is None or not (0 <= score <= 750):
            errs.append(f"row {i}: invalid min_score {score}")
        year = item.get("year")
        if year is None or not (2020 <= year <= 2025):
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
    keys_seen = set()
    for i, item in enumerate(data):
        errs = []
        name = item.get("industry_name", "")
        year = item.get("year")
        if not name:
            errs.append(f"row {i}: missing industry_name")
        key = (name, year)
        if key in keys_seen:
            errs.append(f"row {i}: duplicate industry '{name}' for year {year}")
        keys_seen.add(key)
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
