"""Extractor orchestration for the data link pipeline.

RuleBasedExtractor is the offline fallback and reuses the original keyword
rules. LLMExtractor handles external structured extraction. HybridExtractor is
the default policy: try LLM when explicitly enabled with a key, otherwise use
rules, and fall back to rules if the LLM call or JSON parsing fails.
"""

from __future__ import annotations

from services.data_link import ExtractedStudentInfo, _merge_user_and_ai_info, extractStudentInfo
from services.data_link_llm import LLMExtractor, load_llm_config


class RuleBasedExtractor:
    """Offline extractor that merges rule results from user text and AI reply."""

    name = "rule"

    def extract(self, user_message: str, ai_reply: str | None = None) -> ExtractedStudentInfo:
        user_info = extractStudentInfo(user_message)
        ai_info = extractStudentInfo(ai_reply or "")
        info = _merge_user_and_ai_info(user_info, ai_info)
        info.extractor = self.name
        return info


class HybridExtractor:
    """Default extractor policy used by demo, interactive, and pipeline calls."""

    name = "hybrid"

    def __init__(
        self,
        llm_extractor: LLMExtractor | None = None,
        rule_extractor: RuleBasedExtractor | None = None,
    ):
        self.config = load_llm_config()
        self.llm_extractor = llm_extractor
        self.rule_extractor = rule_extractor or RuleBasedExtractor()

    def extract(self, user_message: str, ai_reply: str | None = None) -> ExtractedStudentInfo:
        if self.config.enabled and self.config.key_found:
            try:
                extractor = self.llm_extractor or LLMExtractor(config=self.config)
                info = extractor.extract(user_message, ai_reply)
                info.extractor = "llm"
                return info
            except Exception as exc:
                print(f"Warning: LLM extraction failed, falling back to rule extractor: {exc}")
                info = self.rule_extractor.extract(user_message, ai_reply)
                info.extractor = "rule_fallback"
                return info

        info = self.rule_extractor.extract(user_message, ai_reply)
        info.extractor = "rule"
        return info
