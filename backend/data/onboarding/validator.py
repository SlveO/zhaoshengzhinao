def validate_admission_row(row: dict) -> str | None:
    required = ["year", "province", "major_name", "min_score", "min_rank"]
    for field in required:
        if row.get(field) is None:
            return f"缺少必填字段: {field}"

    year = int(row["year"])
    if year < 2020 or year > 2030:
        return f"年份超出范围: {year}"

    score = int(row["min_score"])
    if score < 0 or score > 750:
        return f"分数超出范围: {score}"

    rank = int(row["min_rank"])
    if rank <= 0:
        return f"位次必须为正整数: {rank}"

    return None


def validate_curriculum_row(row: dict) -> str | None:
    required = ["major_name", "core_courses"]
    for field in required:
        if row.get(field) is None:
            return f"缺少必填字段: {field}"
    return None


def validate_employment_row(row: dict) -> str | None:
    required = ["major_name", "year", "employment_rate"]
    for field in required:
        if row.get(field) is None:
            return f"缺少必填字段: {field}"

    rate = float(row["employment_rate"])
    if rate < 0 or rate > 100:
        return f"就业率超出 0-100 范围: {rate}"
    return None
