"""Unit tests for persona_service (no I/O, pure logic)."""
import sys
from pathlib import Path

import pytest_asyncio

# Ensure backend/ on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.persona_service import (
    build_persona_greeting,
    apply_persona_style,
    has_legacy_custom_prompt,
)


# 纯单元测试 — 覆盖 conftest.py 的 autouse setup_db，避免连真实 DB
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def test_build_persona_greeting_with_name_and_greeting():
    persona = {"assistant_name": "小招", "greeting": "你好，我是华师招生助手"}
    out = build_persona_greeting(persona, "华南师大")
    assert "小招" in out
    assert "你好，我是华师招生助手" in out
    assert "华南师大" in out


def test_build_persona_greeting_falls_back_to_uni_short():
    persona = {}
    out = build_persona_greeting(persona, "华南师大")
    assert "华南师大招生助手" in out
    assert "你的名字是" in out


def test_build_persona_greeting_without_greeting():
    persona = {"assistant_name": "小招"}
    out = build_persona_greeting(persona, "华南师大")
    assert "小招" in out
    assert "开场白" not in out


def test_apply_persona_style_formal():
    out = apply_persona_style("BASE", {"style": "formal"})
    assert out == "BASE\n\n请使用正式、专业的语气。"


def test_apply_persona_style_casual_noop():
    out = apply_persona_style("BASE", {"style": "casual"})
    assert out == "BASE"


def test_apply_persona_style_empty_noop():
    out = apply_persona_style("BASE", {})
    assert out == "BASE"


def test_has_legacy_custom_prompt_true():
    assert has_legacy_custom_prompt({"custom_prompt": "xxx"}) is True


def test_has_legacy_custom_prompt_false_empty():
    assert has_legacy_custom_prompt({"custom_prompt": ""}) is False


def test_has_legacy_custom_prompt_false_missing():
    assert has_legacy_custom_prompt({}) is False
