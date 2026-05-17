"""Unified event-log writer.

Every significant user/system action is written to the event_logs table.
Analytics modules consume these events — never call each other directly.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from models import async_session


async def write_event(
    tenant_id: uuid.UUID,
    event_type: str,
    *,
    user_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> None:
    """Write a single event synchronously (caller does NOT need to await completion)."""
    async with async_session() as db:
        await db.execute(
            text(
                """
                INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                VALUES (:id, :tenant_id, :event_type, :user_id, :session_id, :payload, :created_at)
                """
            ),
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "event_type": event_type,
                "user_id": user_id,
                "session_id": session_id,
                "payload": json.dumps(payload or {}, ensure_ascii=False),
                "created_at": datetime.now(timezone.utc),
            },
        )
        await db.commit()
