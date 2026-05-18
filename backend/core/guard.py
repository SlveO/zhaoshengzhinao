"""Pluggable session guards for anonymous chat.

Add new guards by creating a class with a check() method and
appending it to DEFAULT_GUARDS. Guards are evaluated in order;
the first failure stops the chain.

Each guard receives (tenant_slug, session_id, ip_address, msg_count, message_text).
Return None to pass, or a dict {code, message} to block.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

# ── Guard interface ──


class BaseGuard(ABC):
    """One guard in the chain. Override check()."""

    @abstractmethod
    async def check(
        self,
        *,
        tenant_slug: str,
        session_id: str,
        ip_address: str,
        msg_count: int,
        message_text: str,
    ) -> dict | None:
        """Return None to allow, or {'code': '...', 'message': '...'} to block."""
        ...


# ── Built-in guards ──


class MessageLimitGuard(BaseGuard):
    """Limit anonymous sessions to N messages total."""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages

    async def check(self, **kwargs) -> dict | None:
        if kwargs["msg_count"] > self.max_messages:
            return {
                "code": "MESSAGE_LIMIT",
                "message": f"免费对话已达上限（{self.max_messages}条）。注册后可继续深入交流～",
            }
        return None


class ContentLengthGuard(BaseGuard):
    """Reject messages that are too short (likely spam / accidental send)."""

    def __init__(self, min_chars: int = 2):
        self.min_chars = min_chars

    async def check(self, **kwargs) -> dict | None:
        text = (kwargs.get("message_text") or "").strip()
        if len(text) < self.min_chars:
            return {"code": "TOO_SHORT", "message": None}  # silent skip
        return None


class RateLimitGuard(BaseGuard):
    """Redis-based per-IP rate limiter for anonymous session creation."""

    def __init__(self, max_sessions_per_hour: int = 10):
        self.max_sessions = max_sessions_per_hour
        self._window = 3600

    async def check(self, **kwargs) -> dict | None:
        ip = kwargs.get("ip_address", "unknown")
        key = f"rate_limit:anon_session:{ip}"

        try:
            from config import settings
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url)
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, self._window)
            if current > self.max_sessions:
                return {
                    "code": "RATE_LIMITED",
                    "message": "访问过于频繁，请稍后再试",
                }
        except Exception:
            pass  # Redis unavailable → allow (fail open)
        return None


# ── Default guard chain ──

DEFAULT_GUARDS: list[BaseGuard] = [
    ContentLengthGuard(min_chars=2),
    MessageLimitGuard(max_messages=20),
]


async def run_guards(
    *,
    tenant_slug: str = "default",
    session_id: str = "",
    ip_address: str = "",
    msg_count: int = 0,
    message_text: str = "",
    guards: list[BaseGuard] | None = None,
) -> dict | None:
    """Run all guards in order. Return the first blocking result, or None if all pass."""
    for g in guards or DEFAULT_GUARDS:
        block = await g.check(
            tenant_slug=tenant_slug,
            session_id=session_id,
            ip_address=ip_address,
            msg_count=msg_count,
            message_text=message_text,
        )
        if block is not None:
            return block
    return None
