"""咨询意图提取三阶段管道：规则前置 + LLM 增强 + 融合校验。

参考企业知识库问答架构（Dify Query Rewriting、LangChain Multi-Query Retriever、Coze 问题理解节点）。

三阶段：
- 阶段 A：规则前置（同步、零成本）— 提取数字、关键词意图判定、专业词典匹配
- 阶段 B：LLM 增强（temperature=0，含上下文+词典+slots）— Query Rewriting + 结构化抽取
- 阶段 C：融合校验 — 合并规则与 LLM 结果，LLM 失败时规则兜底
"""
import json
import logging
import re
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import settings
from services.prompt_service import load_prompt
from services.tenant_major_dictionary import load_tenant_majors, normalize_major, ALIAS_MAP

_logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """意图提取结果。"""
    intent_type: str = "chitchat"  # data_query | policy_query | major_intro | school_info | chitchat
    majors: list[str] = field(default_factory=list)
    province: str = "广东"
    year: int | None = None
    score_query: int | None = None
    rank_query: int | None = None
    need_admission_data: bool = False
    rewritten_query: str = ""

    def to_dict(self) -> dict:
        return {
            "intent_type": self.intent_type,
            "majors": self.majors,
            "province": self.province,
            "year": self.year,
            "score_query": self.score_query,
            "rank_query": self.rank_query,
            "need_admission_data": self.need_admission_data,
            "rewritten_query": self.rewritten_query,
        }


# ──────────────────────────────────────────────────────────────────
# 阶段 A：规则前置（同步、零成本）
# ──────────────────────────────────────────────────────────────────

_DATA_KEYWORDS = ("分数", "位次", "录取线", "最低分", "最高分", "平均分", "多少分", "线差",
                  "投档", "录取概率", "稳上", "冲刺", "保底", "能上", "考上")
_POLICY_KEYWORDS = ("招生章程", "政策", "选科", "选考", "要求", "规则", "志愿", "批次",
                    "提前批", "本科批", "专科批", "调剂", "退档", "提档")
_INTRO_KEYWORDS = ("学什么", "培养方案", "课程", "介绍", "怎么样", "前景", "就业",
                   "方向", "学制", "几年", "学位")
_SCHOOL_INFO_KEYWORDS = ("项目", "2+2", "3+1", "培养模式", "学历", "承认", "正规", "对接",
                         "合作院校", "国外大学", "合作", "学费", "奖学金", "报名", "材料",
                         "流程", "联系方式", "地址", "电话", "师资", "住宿", "校园", "学校简介",
                         "国际商学院", "ibc", "中美", "中英", "中外合作")
_CHITCHAT_KEYWORDS = ("你好", "谢谢", "再见", "hi", "hello", "在吗", "你是谁")

_INTENT_TYPE_RULES = [
    ("data_query", _DATA_KEYWORDS),
    ("policy_query", _POLICY_KEYWORDS),
    ("major_intro", _INTRO_KEYWORDS),
    ("school_info", _SCHOOL_INFO_KEYWORDS),
    ("chitchat", _CHITCHAT_KEYWORDS),
]

# need_admission_data 判定关键词（data_query 时命中任一即为 true）
_ADMISSION_DATA_INDICATORS = (
    "分数", "多少分", "位次", "录取线", "最低分", "最高分", "平均分", "线差",
    "投档", "录取概率", "稳上", "冲刺", "保底", "能上", "考上", "录取",
)


def _rule_extract_intent(
    user_content: str,
    majors_dict: set[str],
    slots: dict,
) -> Intent:
    """阶段 A：规则前置意图提取。

    通过关键词匹配 + 数字正则 + 专业词典匹配得到一个 Intent 草稿。
    不调用 LLM，零成本，作为 LLM 失败时的兜底。
    """
    text = user_content.strip()
    lower = text.lower()

    # 1. intent_type 关键词判定
    intent_type = "chitchat"
    for itype, keywords in _INTENT_TYPE_RULES:
        if any(kw in lower for kw in keywords):
            intent_type = itype
            break

    # 2. 专业名匹配：子串扫描（词典标准名 + 别名表）
    #    直接在原文中查找专业名/别名的子串匹配，避免分词截断问题
    majors: list[str] = []
    for major in majors_dict:
        if major in text and major not in majors:
            majors.append(major)
    for alias, standard in ALIAS_MAP.items():
        if standard in majors_dict and standard not in majors:
            if alias in lower or alias in text:
                majors.append(standard)

    # 3. 数字提取：分数 / 位次 / 年份
    score_query = None
    rank_query = None
    year = None

    # 分数：通常 3 位数（400-750）
    score_match = re.search(r"(\d{3})\s*分", text)
    if score_match:
        val = int(score_match.group(1))
        if 400 <= val <= 750:
            score_query = val

    # 位次：通常带"位/名"
    rank_match = re.search(r"(\d{2,6})\s*(?:位|名)", text)
    if rank_match:
        rank_query = int(rank_match.group(1))

    # 年份：4 位数
    year_match = re.search(r"(20\d{2})\s*年", text)
    if year_match:
        y = int(year_match.group(1))
        if 2020 <= y <= 2030:
            year = y

    # 4. 省份：slots 优先
    province = "广东"
    region_pref = slots.get("region_pref") or slots.get("province")
    if isinstance(region_pref, str):
        province = region_pref
    elif isinstance(region_pref, dict):
        regions = region_pref.get("regions") or []
        if regions:
            province = regions[0]
    elif slots.get("province"):
        province = slots["province"]

    # 5. need_admission_data
    need_admission_data = (
        intent_type == "data_query"
        and (
            score_query is not None
            or rank_query is not None
            or any(kw in text for kw in _ADMISSION_DATA_INDICATORS)
        )
    )

    return Intent(
        intent_type=intent_type,
        majors=majors,
        province=province,
        year=year,
        score_query=score_query,
        rank_query=rank_query,
        need_admission_data=need_admission_data,
        rewritten_query=text,
    )


# ──────────────────────────────────────────────────────────────────
# 阶段 B：LLM 增强
# ──────────────────────────────────────────────────────────────────


def _format_conversation_history(history: list[dict], limit: int = 4) -> str:
    """格式化最近 N 轮对话历史为 prompt 文本。"""
    if not history:
        return "（无历史，这是对话首条消息）"

    recent = history[-limit * 2:] if len(history) > limit * 2 else history
    lines = []
    for m in recent:
        role = "学生" if m.get("role") == "user" else "助手"
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "（无有效历史）"


def _format_slots_summary(slots: dict) -> str:
    """格式化学生画像为 prompt 文本。"""
    if not slots:
        return "（暂无画像信息）"

    parts = []
    if slots.get("province"):
        parts.append(f"省份: {slots['province']}")
    if slots.get("subjects"):
        parts.append(f"选科: {slots['subjects']}")
    if slots.get("score"):
        parts.append(f"分数: {slots['score']}")
    if slots.get("rank"):
        parts.append(f"位次: {slots['rank']}")
    if slots.get("intent_majors"):
        parts.append(f"意向专业: {', '.join(slots['intent_majors'])}")
    riasec = slots.get("riasec")
    if isinstance(riasec, dict) and riasec:
        top = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:2]
        parts.append(f"兴趣维度: {', '.join(f'{k}={v}' for k, v in top)}")
    return "; ".join(parts) if parts else "（暂无画像信息）"


def _format_tenant_majors(majors: set[str]) -> str:
    """格式化专业词典为 prompt 文本。"""
    if not majors:
        return "（词典为空，请基于常识判断专业名）"
    sorted_majors = sorted(majors)
    # 分行显示，避免单行过长
    return "\n".join(f"- {m}" for m in sorted_majors[:80])


def _parse_llm_intent(raw: str, majors_dict: set[str]) -> Intent | None:
    """解析 LLM 返回的 JSON 为 Intent，并校验专业名在词典内。"""
    if not raw:
        return None

    # 提取 JSON（容忍前后多余文本）
    text = raw.strip()
    # 去除可能的 markdown 代码块标记
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # 找到第一个 { 和最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None

    intent_type = data.get("intent_type", "chitchat")
    if intent_type not in ("data_query", "policy_query", "major_intro", "school_info", "chitchat"):
        intent_type = "chitchat"

    # 校验 majors 在词典内
    raw_majors = data.get("majors") or []
    majors: list[str] = []
    for m in raw_majors:
        if not isinstance(m, str):
            continue
        normalized = normalize_major(m, majors_dict)
        if normalized and normalized not in majors:
            majors.append(normalized)

    province = data.get("province") or "广东"
    year = data.get("year")
    if year is not None and not isinstance(year, int):
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = None

    score_query = data.get("score_query")
    if score_query is not None and not isinstance(score_query, int):
        try:
            score_query = int(score_query)
        except (TypeError, ValueError):
            score_query = None

    rank_query = data.get("rank_query")
    if rank_query is not None and not isinstance(rank_query, int):
        try:
            rank_query = int(rank_query)
        except (TypeError, ValueError):
            rank_query = None

    rewritten_query = data.get("rewritten_query") or ""
    if not isinstance(rewritten_query, str):
        rewritten_query = str(rewritten_query)

    need_admission_data = bool(data.get("need_admission_data", False))

    return Intent(
        intent_type=intent_type,
        majors=majors,
        province=province,
        year=year,
        score_query=score_query,
        rank_query=rank_query,
        need_admission_data=need_admission_data,
        rewritten_query=rewritten_query,
    )


async def _llm_extract_intent(
    user_content: str,
    tenant_slug: str,
    history: list[dict],
    slots: dict,
    majors_dict: set[str],
) -> Intent | None:
    """阶段 B：LLM 增强意图提取。失败返回 None。"""
    prompt_template = await load_prompt("consult_intent", tenant_slug)

    conversation_history = _format_conversation_history(history, limit=4)
    slots_summary = _format_slots_summary(slots)
    tenant_majors = _format_tenant_majors(majors_dict)

    try:
        system_content = prompt_template.format(
            conversation_history=conversation_history,
            slots_summary=slots_summary,
            tenant_majors=tenant_majors,
        )
    except KeyError as e:
        _logger.warning(f"INTENT_EXTRACTION_PROMPT missing placeholder: {e}")
        system_content = prompt_template

    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.0,
    )

    msgs = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]
    resp = await llm.ainvoke(msgs)
    return _parse_llm_intent(resp.content, majors_dict)


# ──────────────────────────────────────────────────────────────────
# 阶段 C：融合校验
# ──────────────────────────────────────────────────────────────────


def _fuse_intent(rule_intent: Intent, llm_intent: Intent | None) -> Intent:
    """阶段 C：融合规则与 LLM 结果。

    策略：
    - LLM 成功时以 LLM 为主，但用规则结果补全 LLM 漏掉的字段
    - LLM 失败时直接用规则结果
    - need_admission_data: LLM 判定优先，但规则命中分数/位次关键词时强制为 true
    """
    if llm_intent is None:
        _logger.info("LLM intent failed, falling back to rule intent")
        return rule_intent

    # 以 LLM 为主，规则补漏
    merged = Intent(
        intent_type=llm_intent.intent_type,
        majors=llm_intent.majors if llm_intent.majors else rule_intent.majors,
        province=llm_intent.province or rule_intent.province,
        year=llm_intent.year if llm_intent.year is not None else rule_intent.year,
        score_query=llm_intent.score_query if llm_intent.score_query is not None else rule_intent.score_query,
        rank_query=llm_intent.rank_query if llm_intent.rank_query is not None else rule_intent.rank_query,
        need_admission_data=llm_intent.need_admission_data or rule_intent.need_admission_data,
        rewritten_query=llm_intent.rewritten_query or rule_intent.rewritten_query,
    )

    # 融合校验：data_query 但无 majors 且规则提取到 majors，补回
    if merged.intent_type == "data_query" and not merged.majors and rule_intent.majors:
        merged.majors = rule_intent.majors

    return merged


# ──────────────────────────────────────────────────────────────────
# 公开 API
# ──────────────────────────────────────────────────────────────────


async def extract_intent(
    user_content: str,
    tenant_slug: str,
    history: list[dict],
    slots: dict,
) -> Intent:
    """三阶段意图提取主入口。

    Args:
        user_content: 用户当前消息
        tenant_slug: 租户 slug（用于加载专业词典 + prompt）
        history: 对话历史（list[dict]，每项含 role/content）
        slots: 学生画像快照（province/subjects/score/rank/intent_majors/riasec 等）

    Returns:
        Intent 对象（绝不抛异常，失败时返回规则兜底结果）
    """
    # 加载专业词典
    try:
        majors_dict = await load_tenant_majors(tenant_slug)
    except Exception as e:
        _logger.warning(f"load_tenant_majors failed: {e}")
        majors_dict = set()

    # 阶段 A：规则前置
    rule_intent = _rule_extract_intent(user_content, majors_dict, slots)

    # 阶段 B：LLM 增强
    llm_intent: Intent | None = None
    try:
        llm_intent = await _llm_extract_intent(
            user_content=user_content,
            tenant_slug=tenant_slug,
            history=history,
            slots=slots,
            majors_dict=majors_dict,
        )
    except Exception as e:
        _logger.warning(f"LLM intent extraction failed: {e}")

    # 阶段 C：融合校验
    final_intent = _fuse_intent(rule_intent, llm_intent)

    _logger.info(
        "extract_intent: type=%s majors=%s score=%s rank=%s need_data=%s rewritten=%r",
        final_intent.intent_type, final_intent.majors,
        final_intent.score_query, final_intent.rank_query,
        final_intent.need_admission_data, final_intent.rewritten_query[:60],
    )

    return final_intent
