"""Dialogue quality — compute conversation metrics from chat events."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
async def get_dialogue_quality(tenant_id: str, days: int = 365) -> dict:
    from models import async_session
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        turns_row = await db.execute(text("""
            SELECT ROUND(AVG(max_turns), 1) AS avg_turns
            FROM (
                SELECT session_id,
                       MAX((payload->>'turn')::int) AS max_turns
                FROM event_logs
                WHERE tenant_id = :tid
                  AND event_type = 'chat.message_sent'
                  AND created_at >= :since
                GROUP BY session_id
            ) sub
        """), {"tid": tenant_id, "since": since})
        avg_turns = float(turns_row.scalar() or 0)

        completion_row = await db.execute(text("""
            SELECT
                COUNT(DISTINCT CASE WHEN payload->>'to_stage' = 'confirm' THEN session_id END) * 100.0 /
                NULLIF(COUNT(DISTINCT session_id), 0) AS completion_rate
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'chat.stage_changed'
              AND created_at >= :since
        """), {"tid": tenant_id, "since": since})
        completion_rate = round(float(completion_row.scalar() or 0), 1)

        satisfaction_row = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE payload->>'feedback' = 'useful') * 100.0 /
                NULLIF(COUNT(*), 0) AS satisfaction
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'recommendation.feedback'
              AND created_at >= :since
        """), {"tid": tenant_id, "since": since})
        avg_satisfaction = round(float(satisfaction_row.scalar() or 0), 1)

        questions_row = await db.execute(text("""
            SELECT payload->>'stage' AS question,
                   COUNT(*) AS count
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'chat.message_sent'
              AND created_at >= :since
              AND payload->>'stage' IS NOT NULL
            GROUP BY payload->>'stage'
            ORDER BY count DESC
            LIMIT 10
        """), {"tid": tenant_id, "since": since})
        top_questions = [
            {"question": row.question, "count": row.count}
            for row in questions_row
        ]

    return {
        "metrics": {
            "avgTurnsPerSession": avg_turns,
            "completionRate": completion_rate,
            "avgSatisfaction": avg_satisfaction,
            "topQuestions": top_questions,
        },
    }
