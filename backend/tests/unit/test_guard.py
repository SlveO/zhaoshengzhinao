"""Unit tests for pluggable guard system."""
import asyncio
import pytest
from core.guard import (
    ContentLengthGuard,
    MessageLimitGuard,
    run_guards,
)


class TestContentLengthGuard:
    def test_allow_normal_message(self):
        g = ContentLengthGuard(min_chars=2)
        block = g.check(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=1, message_text="你好"
        )
        assert block is None

    def test_block_too_short_message(self):
        g = ContentLengthGuard(min_chars=2)
        block = g.check(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=1, message_text="a"
        )
        assert block is not None
        assert block["code"] == "TOO_SHORT"

    def test_block_empty_message(self):
        g = ContentLengthGuard(min_chars=2)
        block = g.check(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=1, message_text=""
        )
        assert block is not None
        assert block["code"] == "TOO_SHORT"

    def test_block_whitespace_only(self):
        g = ContentLengthGuard(min_chars=2)
        block = g.check(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=1, message_text="   "
        )
        assert block is not None
        assert block["code"] == "TOO_SHORT"


class TestMessageLimitGuard:
    def test_allow_below_limit(self):
        g = MessageLimitGuard(max_messages=20)
        block = g.check(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=15, message_text="hello"
        )
        assert block is None

    def test_allow_at_limit(self):
        g = MessageLimitGuard(max_messages=20)
        block = g.check(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=20, message_text="hello"
        )
        assert block is None

    def test_block_above_limit(self):
        g = MessageLimitGuard(max_messages=20)
        block = g.check(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=21, message_text="hello"
        )
        assert block is not None
        assert block["code"] == "MESSAGE_LIMIT"

    def test_custom_limit(self):
        g = MessageLimitGuard(max_messages=5)
        block = g.check(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=6, message_text="hello"
        )
        assert block is not None
        assert block["code"] == "MESSAGE_LIMIT"


class TestGuardChain:
    def test_first_guard_blocks_stops_chain(self):
        guards = [
            ContentLengthGuard(min_chars=100),
            MessageLimitGuard(max_messages=5),
        ]
        block = _sync(run_guards(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=10, message_text="hi",
            guards=guards,
        ))
        assert block is not None
        assert block["code"] == "TOO_SHORT"

    def test_all_guards_pass_returns_none(self):
        guards = [
            ContentLengthGuard(min_chars=2),
            MessageLimitGuard(max_messages=20),
        ]
        block = _sync(run_guards(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=5, message_text="hello world",
            guards=guards,
        ))
        assert block is None

    def test_second_guard_blocks_when_first_passes(self):
        guards = [
            ContentLengthGuard(min_chars=2),
            MessageLimitGuard(max_messages=3),
        ]
        block = _sync(run_guards(
            tenant_slug="scnu", session_id="s1", ip_address="",
            msg_count=4, message_text="hello world",
            guards=guards,
        ))
        assert block is not None
        assert block["code"] == "MESSAGE_LIMIT"


def _sync(coro):
    return asyncio.run(coro)
