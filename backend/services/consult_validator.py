"""咨询模块后置校验服务。

校验 LLM 回复中提到的「专业名 + 数字」是否与 admission_rows 一致。
issue_type: mismatch | fabricated | wrong_major
"""
import re
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    major_in_reply: str
    metric: str  # "min_score" | "min_rank"
    value_in_reply: int
    matched_db_row: dict | None
    issue_type: str  # "mismatch" | "fabricated" | "wrong_major"


# 专业名简称映射（校验前标准化）
MAJOR_ALIAS_MAP = {
    "AI": "人工智能",
    "软工": "软件工程",
    "计科": "计算机科学与技术",
    "信管": "信息管理与信息系统",
}


def _extract_major_mentions(reply: str, known_majors: list[str]) -> list[tuple[int, str]]:
    """找到回复中所有专业名提及及其位置。

    匹配来源：
    1. 已知专业名（来自 admission_rows）
    2. 简称（MAJOR_ALIAS_MAP）
    3. "XX专业"模式（用于检测 DB 中不存在的专业，至少 2 个字符）

    Returns:
        [(position, normalized_major_name), ...] 按位置排序
    """
    positions: list[tuple[int, str]] = []

    # 1. 已知专业名
    for major in known_majors:
        for m in re.finditer(re.escape(major), reply):
            positions.append((m.start(), major))

    # 2. 简称
    for alias, full in MAJOR_ALIAS_MAP.items():
        if full in known_majors:
            for m in re.finditer(re.escape(alias), reply):
                positions.append((m.start(), full))

    # 3. "XX专业"模式（检测未知专业）
    for m in re.finditer(r"([\u4e00-\u9fa5A-Za-z]{2,10}?专业)", reply):
        name = m.group()[:-2]  # 去掉"专业"后缀
        if name:
            positions.append((m.start(), name))

    positions.sort(key=lambda x: x[0])
    return positions


def _extract_digit_pairs(reply: str, major_positions: list[tuple[int, str]]) -> list[tuple[str, int]]:
    """提取 (专业名, 数字) pairs，数字归属最近的先前专业名。

    数字规则：3-6 位，排除年份（2000-2030）。
    """
    pairs: list[tuple[str, int]] = []
    for m in re.finditer(r"\d{3,6}", reply):
        d = int(m.group())
        if 2000 <= d <= 2030:  # 排除年份
            continue
        pos = m.start()
        # 找到最近的先前专业名
        nearest_major: str | None = None
        for mp_pos, mp_name in major_positions:
            if mp_pos < pos:
                nearest_major = mp_name
            else:
                break
        if nearest_major:
            pairs.append((nearest_major, d))
    return pairs


def validate_response(
    reply: str,
    admission_rows: list[dict],
) -> list[ValidationIssue]:
    """校验回复中的数字是否与 admission_rows 一致。

    Args:
        reply: LLM 回复文本
        admission_rows: 数据库查询结果

    Returns:
        issues 列表（空列表 = 通过）
    """
    if not admission_rows:
        return []

    known_majors = list({r["major_name"] for r in admission_rows})

    major_positions = _extract_major_mentions(reply, known_majors)
    pairs = _extract_digit_pairs(reply, major_positions)

    if not pairs:
        return []

    issues: list[ValidationIssue] = []
    seen = set()  # 防止重复 issue

    for major_in_reply, value_in_reply in pairs:
        # 查找该专业的 DB 行
        matched_rows = [r for r in admission_rows if r["major_name"] == major_in_reply]

        if not matched_rows:
            # 专业不在 DB 中 → fabricated
            key = (major_in_reply, value_in_reply, "fabricated")
            if key not in seen:
                seen.add(key)
                issues.append(ValidationIssue(
                    major_in_reply=major_in_reply,
                    metric="unknown",
                    value_in_reply=value_in_reply,
                    matched_db_row=None,
                    issue_type="fabricated",
                ))
            continue

        # 检查这个数字是否匹配该专业的任一指标
        matched = any(
            value_in_reply == row["min_score"] or value_in_reply == row["min_rank"]
            for row in matched_rows
        )
        if matched:
            continue

        # 不匹配该专业任何指标
        # 检查是否是其他专业的数字（wrong_major）
        other_major_match = None
        for other_row in admission_rows:
            if other_row["major_name"] == major_in_reply:
                continue
            if value_in_reply in (other_row["min_score"], other_row["min_rank"]):
                other_major_match = other_row
                break

        if other_major_match:
            key = (major_in_reply, value_in_reply, "wrong_major")
            if key not in seen:
                seen.add(key)
                issues.append(ValidationIssue(
                    major_in_reply=major_in_reply,
                    metric="min_rank" if value_in_reply == other_major_match["min_rank"] else "min_score",
                    value_in_reply=value_in_reply,
                    matched_db_row=other_major_match,
                    issue_type="wrong_major",
                ))
        else:
            # 数字不匹配任何专业，是编造的
            # 判断更像分数还是位次（5 位数及以上当位次，否则当分数）
            metric = "min_rank" if value_in_reply >= 10000 else "min_score"
            key = (major_in_reply, value_in_reply, "mismatch")
            if key not in seen:
                seen.add(key)
                issues.append(ValidationIssue(
                    major_in_reply=major_in_reply,
                    metric=metric,
                    value_in_reply=value_in_reply,
                    matched_db_row=matched_rows[0],
                    issue_type="mismatch",
                ))

    return issues
