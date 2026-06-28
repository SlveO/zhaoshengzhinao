"""咨询模块双层检索服务。

Step 2a: query_admission_data — SQL 精确查询 admission_data 表
Step 2b: build_rag_query + search_similar — RAG 向量检索
"""
import logging
import uuid
from sqlalchemy import select, or_

from models import async_session
from models.admission import AdmissionData

_logger = logging.getLogger(__name__)


async def query_admission_data(
    majors: list[str],
    province: str,
    year: int | None,
    tenant_college_id: uuid.UUID,
) -> list[dict]:
    """精确查询 admission_data 表。

    Args:
        majors: 标准化专业名列表
        province: 省份（如"广东"）
        year: 年份（None 时取该专业最新 3 年）
        tenant_college_id: 院校 ID（多租户隔离）

    Returns:
        [{major_name, year, province, batch, min_score, min_rank, subject_requirements}, ...]
    """
    if not majors:
        return []

    try:
        async with async_session() as db:
            # 构建专业名模糊匹配条件（ILIKE）
            major_conditions = []
            for m in majors:
                major_conditions.append(AdmissionData.major_name.ilike(f"%{m}%"))

            stmt = select(AdmissionData).where(
                AdmissionData.college_id == tenant_college_id,
                AdmissionData.province == province,
                or_(*major_conditions),
            )

            if year is not None:
                stmt = stmt.where(AdmissionData.year == year)
                stmt = stmt.order_by(AdmissionData.year.desc())
            else:
                # 取每个专业的最新 3 年
                stmt = stmt.order_by(
                    AdmissionData.major_name.asc(),
                    AdmissionData.year.desc(),
                )

            result = await db.execute(stmt)
            rows = result.scalars().all()

            # year=None 时按专业分组取前 3 年
            if year is None and rows:
                grouped: dict[str, list] = {}
                for r in rows:
                    grouped.setdefault(r.major_name, []).append(r)
                rows = []
                for major_rows in grouped.values():
                    rows.extend(major_rows[:3])

            return [
                {
                    "major_name": r.major_name,
                    "year": r.year,
                    "province": r.province,
                    "batch": r.batch or "",
                    "min_score": r.min_score or 0,
                    "min_rank": r.min_rank or 0,
                    "subject_requirements": r.subject_requirements or "",
                }
                for r in rows
            ]
    except Exception as e:
        _logger.warning(f"query_admission_data failed: {e}")
        return []


def build_rag_query(intent: dict, user_content: str) -> str:
    """根据 intent_type 与 majors 构建 RAG 检索 query。

    优先使用 intent.rewritten_query（LLM 改写、已消解指代的完整问题）；
    回退到基于 intent_type + majors 的规则拼接。

    Returns:
        检索 query 字符串；空串表示跳过 RAG（chitchat 场景）。
    """
    intent_type = intent.get("intent_type", "chitchat")
    majors = intent.get("majors") or []
    province = intent.get("province") or "广东"
    year = intent.get("year")
    rewritten = intent.get("rewritten_query") or ""

    if intent_type == "chitchat":
        return ""

    # 优先使用 LLM 改写的 query（已消解指代，检索质量更高）
    if rewritten and rewritten.strip():
        # 改写 query 已包含上下文，但仍补充专业名确保命中
        if majors and not any(m in rewritten for m in majors):
            rewritten = f"{rewritten} {' '.join(majors)}"
        return rewritten.strip()

    if not majors:
        # 无专业名时用原始 user_content
        if intent_type == "data_query":
            return user_content
        elif intent_type == "policy_query":
            return f"{user_content} 招生政策"
        elif intent_type == "major_intro":
            return f"{user_content} 专业介绍"
        elif intent_type == "school_info":
            return f"{user_content} 华南师范大学 国际商学院 项目"
        return user_content

    majors_str = " ".join(majors)

    if intent_type == "data_query":
        year_str = f" {year}" if year else ""
        return f"{majors_str} 录取 分数 位次{year_str} {province}"
    elif intent_type == "policy_query":
        return f"{majors_str} 招生章程 选科要求 培养方案"
    elif intent_type == "major_intro":
        return f"{majors_str} 专业介绍 课程 就业前景"
    return user_content


def render_admission_table(admission_rows: list[dict]) -> str:
    """将 admission_rows 渲染为 Markdown 表格字符串。"""
    if not admission_rows:
        return "（暂无相关录取数据）"

    header = "| 专业 | 年份 | 省份 | 批次 | 最低分 | 最低位次 | 选科要求 |"
    separator = "|------|------|------|------|--------|----------|----------|"
    lines = [header, separator]
    for r in admission_rows:
        lines.append(
            f"| {r['major_name']} | {r['year']} | {r['province']} | {r['batch']} | "
            f"{r['min_score']} | {r['min_rank']} | {r['subject_requirements']} |"
        )
    return "\n".join(lines)
