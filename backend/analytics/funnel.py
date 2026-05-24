"""Enrollment funnel — aggregate event_logs into visitor→enrolled conversion stages."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
async def get_funnel(tenant_id: str, days: int = 365) -> dict:
    from models import async_session
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        visitors = await db.execute(text("""
            SELECT COUNT(DISTINCT user_id)
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'page.viewed'
              AND created_at >= :since
        """), {"tid": tenant_id, "since": since})
        visitor_count = visitors.scalar() or 0

        conversations = await db.execute(text("""
            SELECT COUNT(DISTINCT session_id)
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'chat.message_sent'
              AND created_at >= :since
        """), {"tid": tenant_id, "since": since})
        conversation_count = conversations.scalar() or 0

        deep = await db.execute(text("""
            SELECT COUNT(DISTINCT session_id)
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'profile.updated'
              AND payload->>'completeness' IN ('L2', 'L3')
              AND created_at >= :since
        """), {"tid": tenant_id, "since": since})
        deep_count = deep.scalar() or 0

        intent = await db.execute(text("""
            SELECT COUNT(DISTINCT user_id)
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'page.intent_expressed'
              AND created_at >= :since
        """), {"tid": tenant_id, "since": since})
        intent_count = intent.scalar() or 0

        enrolled_count = 0

    return {
        "period": {
            "start": since.isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
        },
        "stages": {
            "visitors": visitor_count,
            "conversations": conversation_count,
            "deepConsultations": deep_count,
            "intentExpressed": intent_count,
            "enrolled": enrolled_count,
        },
        "conversionRates": {
            "visitorToConversation": round(conversation_count / visitor_count * 100, 1) if visitor_count else 0,
            "conversationToDeep": round(deep_count / conversation_count * 100, 1) if conversation_count else 0,
            "deepToIntent": round(intent_count / deep_count * 100, 1) if deep_count else 0,
            "intentToEnrolled": 0,
        },
    }
