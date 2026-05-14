"""Profile Analyzer — standalone LLM agent that extracts evidence from conversation turns."""
import json, re
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config import settings
from agents.conversation.evidence_accumulator import RIASEC_DIMS, RIASEC_KEYS

ANALYZER_SYSTEM_PROMPT = """你是一位专业的心理学评估分析员。你的任务是从对话中提取用户画像证据。

## 核心原则
1. 只提取本轮对话中**新出现**的证据，不要重复已有证据
2. 每条证据必须引用用户的**原话**
3. 找不到新证据就返回空列表——不要编造
4. 参与度评估要基于用户本轮的回应质量

## RIASEC 维度参考
- R (动手操作): 实验、制作、修理、工具操作、组装
- I (研究思考): 分析、探索、理论、逻辑推理、钻研问题
- A (艺术创造): 设计、创作、表达、想象、写作、绘画
- S (帮助他人): 助人、教育、志愿服务、合作、沟通
- E (领导说服): 管理、组织、说服、竞争、商业思维
- C (规范有序): 整理、数据处理、规则遵守、会计、条理

## 参与度评估标准
- low: 学生回答敷衍（"不知道""随便""都行"），回避开放式问题
- medium: 学生给出具体回答，有一定细节，愿意参与对话
- high: 学生主动分享经历，表达真实情感，回答内容丰富

## 已有证据（不要重复）
{existing_evidence}

## 未探索维度提示
{blind_spot_hint}

## 输出格式
严格按 JSON 格式输出（不要 markdown 代码块标记）：
{{
  "new_evidence": [
    {{
      "dimension": "riasec_X",
      "user_quote": "用户原话",
      "inferred_score": 7,
      "rationale": "推断理由",
      "confidence": 0.7
    }}
  ],
  "values_hint": "价值观关键词或null",
  "region_mentioned": "提及的地区或null",
  "engagement_assessment": {{
    "trust_level": "low/medium/high",
    "willingness_to_share": 0.5,
    "indicators": ["具体指标"]
  }}
}}"""


def build_analysis_prompt(user_msg: str, ai_reply: str, existing_evidence: dict, blind_spots: list[str]) -> str:
    evidence_summary = _summarize_evidence(existing_evidence)
    blind_hint = ""
    if blind_spots:
        labels = [f"{k}({RIASEC_DIMS.get(k, '')})" for k in blind_spots]
        blind_hint = f"注意：以下维度尚无证据，优先从本轮对话中识别：{', '.join(labels)}"
    else:
        blind_hint = "所有 RIASEC 维度均已覆盖，关注价值观和深层次偏好。"
    system_prompt = ANALYZER_SYSTEM_PROMPT.format(
        existing_evidence=evidence_summary,
        blind_spot_hint=blind_hint,
    )
    return f"{system_prompt}\n\n## 本轮对话\n用户消息：{user_msg}\nAI回复：{ai_reply}"


def _summarize_evidence(evidence: dict) -> str:
    lines = []
    for k in RIASEC_KEYS:
        e = evidence.get(k, {})
        if e.get("evidence_count", 0) > 0:
            lines.append(f"- {k}: {e['evidence_count']}条证据, 当前评分{e.get('score')}, 置信度{e.get('confidence')}")
    values = evidence.get("values", {})
    if values.get("ranked"):
        lines.append(f"- 价值观: {' > '.join(values['ranked'])}")
    return "\n".join(lines) if lines else "尚无证据"


def parse_analysis_response(text: str) -> dict:
    """Parse LLM response. Returns dict with new_evidence, values_hint, region_mentioned, engagement_assessment."""
    default = {
        "new_evidence": [],
        "values_hint": None,
        "region_mentioned": None,
        "engagement_assessment": {"trust_level": "low", "willingness_to_share": 0.3, "indicators": []},
    }
    # Strip markdown code blocks
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default

    result = {
        "new_evidence": data.get("new_evidence", []),
        "values_hint": data.get("values_hint"),
        "region_mentioned": data.get("region_mentioned"),
        "engagement_assessment": data.get("engagement_assessment", default["engagement_assessment"]),
    }
    # Validate evidence items
    valid_evidence = []
    for item in result["new_evidence"]:
        if item.get("dimension") in RIASEC_KEYS and item.get("user_quote"):
            valid_evidence.append(item)
    result["new_evidence"] = valid_evidence
    return result


async def analyze_turn(user_msg: str, ai_reply: str, evidence: dict, blind_spots: list[str]) -> dict:
    """Call LLM to analyze a conversation turn and return parsed evidence."""
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.2,
    )
    system = SystemMessage(content=build_analysis_prompt(user_msg, ai_reply, evidence, blind_spots))
    human = HumanMessage(content="请分析并输出JSON。")
    try:
        response = await llm.ainvoke([system, human])
        return parse_analysis_response(response.content)
    except Exception:
        return parse_analysis_response("")
