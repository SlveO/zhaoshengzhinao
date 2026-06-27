"""Persona service: assemble AI persona (greeting + style) for system prompts.

Used by both recommendation (chat.py) and consultation (consult.py) modules
to inject assistant_name/greeting/style consistently.
"""
from __future__ import annotations

from typing import Any


def build_persona_greeting(persona: dict[str, Any], uni_short: str) -> str:
    """Assemble persona greeting block (prepended to system prompt).

    Args:
        persona: ai_persona dict from tenant config (may be empty).
        uni_short: university short name (e.g. "华南师大").

    Returns:
        Multi-line greeting string. Always non-empty.
    """
    name = persona.get("assistant_name") or f"{uni_short}招生助手"
    parts = [f"你的名字是「{name}」，代表 {uni_short} 招生办为学生提供咨询服务。"]
    greeting = persona.get("greeting", "")
    if greeting:
        parts.append(f"开场白/自我介绍：{greeting}")
    return "\n".join(parts)


def apply_persona_style(system_content: str, persona: dict[str, Any]) -> str:
    """Append style hint to system prompt.

    Args:
        system_content: existing system prompt.
        persona: ai_persona dict; style 'formal' triggers formal hint.

    Returns:
        system_content possibly with formal-style suffix.
    """
    if persona.get("style") == "formal":
        return system_content + "\n\n请使用正式、专业的语气。"
    return system_content


def has_legacy_custom_prompt(persona: dict[str, Any]) -> bool:
    """Detect legacy custom_prompt for backward-compat fallback.

    Args:
        persona: ai_persona dict.

    Returns:
        True if non-empty custom_prompt exists.
    """
    return bool(persona.get("custom_prompt"))
