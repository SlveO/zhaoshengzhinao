"""LLM-backed structured extraction for the data link pipeline.

The API key is read only from environment variables and is never printed or
stored in JSON outputs. Tests should inject fake clients; real network calls are
reserved for local/manual runs with DATA_LINK_LLM_ENABLED=true.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from services.data_link import ExtractedStudentInfo


VALID_SUBJECT_TYPES = {"物理类", "历史类", "理科", "文科"}
VALID_RISK_PREFERENCES = {"冲刺", "稳妥", "保底", "未知"}
CONCERN_NORMALIZATION = {
    "录取概率": ["录取概率", "稳不稳", "滑档", "冲刺", "录取机会"],
    "专业分数线": ["专业分数线", "分数线", "最低分", "往年分数"],
    "就业前景": ["就业前景", "就业"],
    "宿舍": ["宿舍", "寝室"],
    "学费": ["学费", "收费"],
    "转专业": ["转专业", "换专业"],
    "保研": ["保研", "推免"],
    "校园环境": ["校园环境", "校园", "环境"],
    "招生政策": ["招生政策", "政策"],
    "报名方式": ["报名方式", "报名"],
    "招生联系方式": ["招生联系方式", "联系方式", "电话", "老师微信", "招生群"],
}


class LLMExtractionError(RuntimeError):
    """Raised when an LLM response cannot be used for structured extraction."""


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str: ...


@dataclass
class DataLinkLLMConfig:
    enabled: bool
    provider: str
    api_key: str
    base_url: str
    model: str
    timeout: float

    @property
    def key_found(self) -> bool:
        return bool(self.api_key)


def load_llm_config() -> DataLinkLLMConfig:
    return DataLinkLLMConfig(
        enabled=os.getenv("DATA_LINK_LLM_ENABLED", "").lower() == "true",
        provider=os.getenv("DATA_LINK_LLM_PROVIDER", "deepseek"),
        api_key=os.getenv("DATA_LINK_LLM_API_KEY", ""),
        base_url=os.getenv("DATA_LINK_LLM_BASE_URL", "https://api.deepseek.com/v1/chat/completions"),
        model=os.getenv("DATA_LINK_LLM_MODEL", "deepseek-chat"),
        timeout=float(os.getenv("DATA_LINK_LLM_TIMEOUT", "20") or 20),
    )


class OpenAICompatibleLLMClient:
    def __init__(self, config: DataLinkLLMConfig):
        self.config = config

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": "你是高校招生咨询数据结构化抽取助手，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMExtractionError(f"LLM request failed: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMExtractionError("LLM response missing choices[0].message.content") from exc


class LLMExtractor:
    """Call an OpenAI-compatible LLM and normalize the returned JSON."""

    name = "llm"

    def __init__(
        self,
        config: DataLinkLLMConfig | None = None,
        client: LLMClient | None = None,
    ):
        self.config = config or load_llm_config()
        self.client = client or OpenAICompatibleLLMClient(self.config)

    def extract(self, user_message: str, ai_reply: str | None = None) -> ExtractedStudentInfo:
        if not self.config.enabled:
            raise LLMExtractionError("LLM extraction is disabled")
        if not self.config.api_key:
            raise LLMExtractionError("LLM API key is missing")

        prompt = build_extraction_prompt(user_message, ai_reply)
        response_text = self.client.complete(prompt)
        raw = parse_llm_json(response_text)
        info = normalize_llm_extracted_info(raw, raw_text=user_message or "")
        info.extractor = self.name
        return info


def build_extraction_prompt(user_message: str, ai_reply: str | None = None) -> str:
    return f"""
请从高校招生咨询对话中抽取结构化学生画像字段。

学生输入 userMessage:
{user_message or ""}

AI 回复 aiReply:
{ai_reply or ""}

只输出 JSON，不要输出解释文字。JSON schema:
{{
  "province": "广东 或 null",
  "subjectType": "物理类/历史类/理科/文科 或 null",
  "score": 585,
  "rank": 32000,
  "interestedMajors": ["人工智能", "软件工程"],
  "concerns": ["录取概率", "专业分数线", "就业前景"],
  "riskPreference": "冲刺/稳妥/保底/未知",
  "intentSignals": ["提供分数", "明确专业意向"],
  "summary": "一句话学生画像概括",
  "confidence": 0.92
}}

字段规范:
- 没有明确提供的字段用 null 或空数组，不要编造。
- subjectType 只能是 物理类、历史类、理科、文科。
- concerns 尽量归一到：录取概率、专业分数线、就业前景、宿舍、学费、转专业、保研、校园环境、招生政策、报名方式、招生联系方式。
- AI 回复提到的推荐专业可以加入 interestedMajors，但不要把泛泛提到的所有专业都当作强意向。
""".strip()


def parse_llm_json(text: str) -> dict[str, Any]:
    candidate = _strip_markdown_json(text)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMExtractionError("Failed to parse LLM JSON") from exc
    if not isinstance(data, dict):
        raise LLMExtractionError("LLM JSON root must be an object")
    return data


def _strip_markdown_json(text: str) -> str:
    content = (text or "").strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.S | re.I)
    return match.group(1).strip() if match else content


def normalize_llm_extracted_info(raw: dict[str, Any], raw_text: str = "") -> ExtractedStudentInfo:
    province = _clean_str_or_none(raw.get("province"))
    subject_type = _normalize_subject_type(raw.get("subjectType"))
    score = _to_int_or_none(raw.get("score"))
    rank = _to_int_or_none(raw.get("rank"))
    majors = _dedupe(_to_str_list(raw.get("interestedMajors")))
    concerns = _dedupe(_normalize_concerns(_to_str_list(raw.get("concerns"))))
    intent_signals = _dedupe(_to_str_list(raw.get("intentSignals")))
    risk_preference = _normalize_risk_preference(raw.get("riskPreference"))
    summary = _clean_str_or_none(raw.get("summary"))
    confidence = _clamp_float(raw.get("confidence"))
    contact_intent = True if {"报名方式", "招生联系方式"}.intersection(concerns) else None

    return ExtractedStudentInfo(
        province=province,
        subjectType=subject_type,
        score=score,
        rank=rank,
        interestedMajors=majors,
        concerns=concerns,
        contactIntent=contact_intent,
        rawText=raw_text,
        extractor="llm",
        riskPreference=risk_preference,
        intentSignals=intent_signals,
        summary=summary,
        confidence=confidence,
    )


def _clean_str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "未知"}:
        return None
    return text


def _normalize_subject_type(value: Any) -> str | None:
    text = _clean_str_or_none(value)
    return text if text in VALID_SUBJECT_TYPES else None


def _to_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def _to_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        return [part.strip() for part in re.split(r"[,，、/；;]", text) if part.strip()]
    return [str(value).strip()] if str(value).strip() else []


def _normalize_concerns(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        matched = False
        for name, aliases in CONCERN_NORMALIZATION.items():
            if value == name or any(alias in value for alias in aliases):
                normalized.append(name)
                matched = True
                break
        if not matched:
            normalized.append(value)
    return normalized


def _normalize_risk_preference(value: Any) -> str | None:
    text = _clean_str_or_none(value)
    if not text:
        return None
    for item in VALID_RISK_PREFERENCES:
        if item in text:
            return item
    return None


def _clamp_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number))


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
