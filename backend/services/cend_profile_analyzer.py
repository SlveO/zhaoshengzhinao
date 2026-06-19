"""C-end Profile Analyzer — standalone LLM extractor for student portrait from conversation turns.

Independent LLM extractor for the C-end (student-facing) mini-app.
Reuses profile_analyzer.py's JSON parsing pattern with a dedicated C-end prompt template.
Produces a 7-field structured profile from student dialogue.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from config import settings
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (mirror evidence_accumulator for convenience, avoid circular imports)
# ---------------------------------------------------------------------------

RIASEC_DIMS = {
    "R": "动手操作 (Realistic)",
    "I": "研究思考 (Investigative)",
    "A": "艺术创造 (Artistic)",
    "S": "帮助他人 (Social)",
    "E": "领导说服 (Enterprising)",
    "C": "规范有序 (Conventional)",
}

RIASEC_KEYS = list(RIASEC_DIMS.keys())

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

CEND_ANALYZER_PROMPT = """你是一位专业的招生咨询分析员。你的任务是从高考生与AI咨询师的对话中提取结构化画像。

## 核心原则
1. **增量提取**: 只提取本轮对话中**新出现**的证据，不要重复已有信息
2. **引用原话**: 提取的信息必须基于用户的**原话**，不得臆测
3. **宁缺毋滥**: 找不到新信息就返回空值/null——不要编造
4. **渐进深化**: 学生可能在多轮中逐步透露信息，每次只补充新增部分

## RIASEC 维度参考 (评分 1-10)
- **R (动手操作)**: 喜欢实验、制作、修理、工具操作、动手组装。高分表示偏好实践操作型工作。
- **I (研究思考)**: 喜欢分析、探索、理论钻研、逻辑推理、解决复杂问题。高分表示偏好研究型工作。
- **A (艺术创造)**: 喜欢设计、创作、表达、想象、写作、绘画。高分表示偏好创意型工作。
- **S (帮助他人)**: 喜欢助人、教育、志愿服务、合作、沟通。高分表示偏好社会服务型工作。
- **E (领导说服)**: 喜欢管理、组织、说服、竞争、商业策划。高分表示偏好领导型工作。
- **C (规范有序)**: 喜欢整理、数据处理、规则遵守、条理清晰。高分表示偏好规范型工作。

## 价值观类别
可能的价值观包括但不限于: 社会贡献、个人成长、工作稳定、薪资水平、工作生活平衡、创新机会、专业对口、地域偏好

## 已有画像摘要
{existing_profile_summary}

## 输出格式
严格按 JSON 格式输出（不要 markdown 代码块标记）:
{{
  "basic": {{
    "province": "省份或null",
    "subject_type": "物理类/历史类/未知/null",
    "score": 分数或null
  }},
  "interests": {{
    "preferred_subjects": ["偏好的科目"],
    "strong_subjects": ["擅长的科目"],
    "hobbies": ["兴趣爱好"]
  }},
  "concerns": ["学生关心的标签/问题"],
  "riasec": {{
    "R": 1-10或0表示未提及,
    "I": 1-10或0,
    "A": 1-10或0,
    "S": 1-10或0,
    "E": 1-10或0,
    "C": 1-10或0
  }},
  "values": ["价值观关键词"],
  "region_pref": {{
    "province": "意向省份或null",
    "city": "意向城市或null"
  }},
  "extra": {{}}
}}"""

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class CendExtractionResult:
    """Structured student profile extracted from a single conversation turn."""

    basic: dict = field(default_factory=lambda: {"province": None, "subject_type": None, "score": None})
    interests: dict = field(default_factory=lambda: {"preferred_subjects": [], "strong_subjects": [], "hobbies": []})
    concerns: list = field(default_factory=list)
    riasec: dict = field(default_factory=lambda: {k: 0 for k in RIASEC_KEYS})
    values: list = field(default_factory=list)
    region_pref: dict = field(default_factory=lambda: {"province": None, "city": None})
    extra: dict = field(default_factory=dict)
    completeness: str = "L1"

    def to_profile_json(self) -> dict:
        """Export as a flat JSON-serializable dict suitable for API responses and storage."""
        return {
            "basic": dict(self.basic),
            "interests": {
                "preferred_subjects": list(self.interests.get("preferred_subjects", [])),
                "strong_subjects": list(self.interests.get("strong_subjects", [])),
                "hobbies": list(self.interests.get("hobbies", [])),
            },
            "concerns": list(self.concerns),
            "riasec": dict(self.riasec),
            "values": list(self.values),
            "region_pref": dict(self.region_pref),
            "extra": dict(self.extra),
            "completeness": self.completeness,
        }

    def has_any_data(self) -> bool:
        """Return True if at least one field has meaningful data."""
        basic = self.basic
        if basic.get("province") or basic.get("subject_type") or basic.get("score"):
            return True
        interests = self.interests
        if interests.get("preferred_subjects") or interests.get("strong_subjects") or interests.get("hobbies"):
            return True
        if self.concerns:
            return True
        if any(v > 0 for v in self.riasec.values()):
            return True
        if self.values:
            return True
        if self.region_pref.get("province") or self.region_pref.get("city"):
            return True
        if self.extra:
            return True
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _summarize_existing(existing_profile: Optional[dict]) -> str:
    """Convert an existing profile dict into a readable Chinese summary for prompt injection.

    Returns a brief description or a '暂无' placeholder when the profile is empty/None.
    """
    if not existing_profile:
        return "暂无已有画像数据。"

    lines = []

    basic = existing_profile.get("basic", {})
    if basic:
        parts = []
        if basic.get("province"):
            parts.append(f"省份: {basic['province']}")
        if basic.get("subject_type"):
            parts.append(f"选科: {basic['subject_type']}")
        if basic.get("score"):
            parts.append(f"分数: {basic['score']}")
        if parts:
            lines.append("基本信息: " + ", ".join(parts))

    interests = existing_profile.get("interests", {})
    if interests:
        iparts = []
        if interests.get("preferred_subjects"):
            iparts.append(f"偏好科目: {', '.join(interests['preferred_subjects'])}")
        if interests.get("strong_subjects"):
            iparts.append(f"擅长科目: {', '.join(interests['strong_subjects'])}")
        if interests.get("hobbies"):
            iparts.append(f"爱好: {', '.join(interests['hobbies'])}")
        if iparts:
            lines.append("兴趣: " + "; ".join(iparts))

    riasec = existing_profile.get("riasec", {})
    if riasec:
        nonzero = {k: v for k, v in riasec.items() if v and v > 0}
        if nonzero:
            dim_labels = [f"{k}({RIASEC_DIMS.get(k, '')}): {v}" for k, v in nonzero.items()]
            lines.append("RIASEC: " + ", ".join(dim_labels))

    values = existing_profile.get("values", [])
    if values:
        lines.append(f"价值观: {', '.join(values)}")

    concerns = existing_profile.get("concerns", [])
    if concerns:
        lines.append(f"关注点: {', '.join(concerns)}")

    region = existing_profile.get("region_pref", {})
    if region:
        rparts = []
        if region.get("province"):
            rparts.append(f"省份: {region['province']}")
        if region.get("city"):
            rparts.append(f"城市: {region['city']}")
        if rparts:
            lines.append("地域偏好: " + ", ".join(rparts))

    if not lines:
        return "暂无已有画像数据。"

    return "\n".join(lines)


def build_cend_analysis_prompt(
    user_msg: str,
    ai_reply: str,
    existing_profile: Optional[dict],
) -> str:
    """Build the full prompt string for the LLM call.

    Injects the summarized existing profile into the system prompt template
    and appends the current turn's user message and AI reply.
    """
    summary = _summarize_existing(existing_profile)
    system_prompt = CEND_ANALYZER_PROMPT.format(existing_profile_summary=summary)
    return f"{system_prompt}\n\n## 本轮对话\n用户消息: {user_msg}\nAI回复: {ai_reply}"


def _compute_completeness(result: "CendExtractionResult") -> str:
    """Compute profile completeness level.

    L3 (高): >=4 RIASEC dimensions non-zero AND values list non-empty.
    L2 (中): >=2 RIASEC dimensions non-zero AND region_pref has data.
    L1 (低): otherwise.
    """
    riasec_covered = sum(1 for v in result.riasec.values() if v > 0)
    has_values = len(result.values) >= 1
    has_region = bool(
        (result.region_pref.get("province") or result.region_pref.get("city"))
    )

    if riasec_covered >= 4 and has_values:
        return "L3"
    elif riasec_covered >= 2 and has_region:
        return "L2"
    return "L1"


# ---------------------------------------------------------------------------
# Parsing & merge
# ---------------------------------------------------------------------------


def parse_cend_response(text: str) -> CendExtractionResult:
    """Parse the LLM JSON response into a CendExtractionResult.

    Handles markdown code-block wrapping, validates field types, and returns
    an empty/default result on any parse failure.
    """
    default = CendExtractionResult()

    if not text or not text.strip():
        return default

    clean = text.strip()

    # Strip markdown code block fences
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*\n?", "", clean)
        clean = re.sub(r"\n?```\s*$", "", clean)

    try:
        data = json.loads(clean)
    except (json.JSONDecodeError, TypeError):
        return default

    if not isinstance(data, dict):
        return default

    result = CendExtractionResult()

    # --- basic ---
    basic_raw = data.get("basic", {})
    if isinstance(basic_raw, dict):
        province = basic_raw.get("province")
        if isinstance(province, str) and province.strip():
            result.basic["province"] = province.strip()
        subject_type = basic_raw.get("subject_type")
        if isinstance(subject_type, str) and subject_type.strip():
            result.basic["subject_type"] = subject_type.strip()
        score_raw = basic_raw.get("score")
        if isinstance(score_raw, (int, float)) and score_raw is not None:
            result.basic["score"] = int(score_raw)
        elif isinstance(score_raw, str) and score_raw.strip().isdigit():
            result.basic["score"] = int(score_raw.strip())

    # --- interests ---
    interests_raw = data.get("interests", {})
    if isinstance(interests_raw, dict):
        for field_name in ("preferred_subjects", "strong_subjects", "hobbies"):
            raw = interests_raw.get(field_name, [])
            if isinstance(raw, list):
                cleaned = [str(item).strip() for item in raw if item and str(item).strip()]
                result.interests[field_name] = cleaned

    # --- concerns ---
    concerns_raw = data.get("concerns", [])
    if isinstance(concerns_raw, list):
        result.concerns = [str(c).strip() for c in concerns_raw if c and str(c).strip()]

    # --- riasec ---
    riasec_raw = data.get("riasec", {})
    if isinstance(riasec_raw, dict):
        for k in RIASEC_KEYS:
            v = riasec_raw.get(k, 0)
            try:
                vi = int(v)
                if 1 <= vi <= 10:
                    result.riasec[k] = vi
                elif vi == 0:
                    result.riasec[k] = 0
                # Values outside 0-10 are ignored (stay 0)
            except (ValueError, TypeError):
                pass

    # --- values ---
    values_raw = data.get("values", [])
    if isinstance(values_raw, list):
        result.values = [str(v).strip() for v in values_raw if v and str(v).strip()]

    # --- region_pref ---
    region_raw = data.get("region_pref", {})
    if isinstance(region_raw, dict):
        province = region_raw.get("province")
        if isinstance(province, str) and province.strip():
            result.region_pref["province"] = province.strip()
        city = region_raw.get("city")
        if isinstance(city, str) and city.strip():
            result.region_pref["city"] = city.strip()

    # --- extra ---
    extra_raw = data.get("extra", {})
    if isinstance(extra_raw, dict):
        result.extra = extra_raw

    # --- completeness ---
    result.completeness = _compute_completeness(result)

    return result


def merge_extraction_results(
    existing: CendExtractionResult,
    new_extraction: CendExtractionResult,
) -> CendExtractionResult:
    """Deep-merge a new extraction into an existing profile.

    Rules:
    - Scalar fields (basic, region_pref): new overrides old when non-None.
    - List fields (concerns, values): union with deduplication, preserving order.
    - RIASEC scores: non-zero values in new override old (0 = "not mentioned").
    - Interests: list sub-fields union-dedup; new overrides old for scalars.
    - extra: shallow merge, new keys override old.
    - completeness: recomputed from merged result.
    """
    merged = CendExtractionResult()

    # --- basic: new overrides old for non-None values ---
    merged.basic["province"] = new_extraction.basic.get("province") or existing.basic.get("province")
    merged.basic["subject_type"] = new_extraction.basic.get("subject_type") or existing.basic.get("subject_type")
    merged.basic["score"] = new_extraction.basic.get("score") or existing.basic.get("score")

    # --- interests: list fields dedup-merge ---
    for field_name in ("preferred_subjects", "strong_subjects", "hobbies"):
        existing_list = list(existing.interests.get(field_name, []))
        new_list = list(new_extraction.interests.get(field_name, []))
        merged_list = _dedup_merge_lists(existing_list, new_list)
        merged.interests[field_name] = merged_list

    # --- concerns: dedup-merge ---
    merged.concerns = _dedup_merge_lists(
        list(existing.concerns),
        list(new_extraction.concerns),
    )

    # --- riasec: nonzero override ---
    for k in RIASEC_KEYS:
        new_val = new_extraction.riasec.get(k, 0)
        existing_val = existing.riasec.get(k, 0)
        merged.riasec[k] = new_val if new_val > 0 else existing_val

    # --- values: dedup-merge ---
    merged.values = _dedup_merge_lists(
        list(existing.values),
        list(new_extraction.values),
    )

    # --- region_pref: new overrides old ---
    merged.region_pref["province"] = new_extraction.region_pref.get("province") or existing.region_pref.get("province")
    merged.region_pref["city"] = new_extraction.region_pref.get("city") or existing.region_pref.get("city")

    # --- extra: shallow merge, new overrides old ---
    merged.extra = dict(existing.extra)
    merged.extra.update(new_extraction.extra)

    # --- recompute completeness ---
    merged.completeness = _compute_completeness(merged)

    return merged


def _dedup_merge_lists(existing_list: list, new_list: list) -> list:
    """Merge two lists preserving order: existing items first, then new items not already present."""
    seen = set()
    result = []
    for item in existing_list:
        if item not in seen:
            seen.add(item)
            result.append(item)
    for item in new_list:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Main async entry-point
# ---------------------------------------------------------------------------


async def analyze_cend_turn(
    user_msg: str,
    ai_reply: str,
    existing_profile: Optional[dict] = None,
    _conversation_history: Optional[list] = None,
    max_retries: int = 2,
) -> CendExtractionResult:
    """Call DeepSeek LLM to extract structured student profile from a conversation turn.

    Implements retry with exponential backoff (1s -> 2s) per project code-style rules.

    Args:
        user_msg: The student's latest message.
        ai_reply: The AI assistant's latest reply.
        existing_profile: Previously accumulated profile dict (from prior turns).
        conversation_history: Reserved for future use (full message history).
        max_retries: Maximum retry attempts on LLM failure (default 2).

    Returns:
        CendExtractionResult populated from the LLM response, or empty/default on error.
    """
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.2,
    )

    system_content = build_cend_analysis_prompt(user_msg, ai_reply, existing_profile)
    system_msg = SystemMessage(content=system_content)
    human_msg = HumanMessage(content="请分析上述对话并输出JSON。")

    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            response = await llm.ainvoke([system_msg, human_msg])
            return parse_cend_response(response.content)
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = 2 ** attempt  # 1s, 2s
                logger.warning(
                    f"C-end profile analysis attempt {attempt + 1} failed: {exc}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"C-end profile analysis failed after {max_retries + 1} attempts: {exc}",
                    exc_info=True,
                )
    return CendExtractionResult()
