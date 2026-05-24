"""Major heatmap — aggregate recommendation + intent events to rank majors by interest."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
async def get_major_heatmap(tenant_id: str, days: int = 365) -> dict:
    from models import async_session
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        feedback_rows = await db.execute(text("""
            SELECT payload->>'major_name' AS major_name,
                   COUNT(*) AS recommendation_count
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'recommendation.feedback'
              AND created_at >= :since
              AND payload->>'major_name' IS NOT NULL
            GROUP BY payload->>'major_name'
        """), {"tid": tenant_id, "since": since})
        major_feedback = {row.major_name: row.recommendation_count for row in feedback_rows}

        intent_rows = await db.execute(text("""
            SELECT major AS major_name,
                   COUNT(*) AS intent_count
            FROM event_logs,
                 jsonb_array_elements_text(payload->'majors_of_interest') AS major
            WHERE tenant_id = :tid
              AND event_type = 'page.intent_expressed'
              AND created_at >= :since
              AND payload->'majors_of_interest' IS NOT NULL
              AND jsonb_typeof(payload->'majors_of_interest') = 'array'
            GROUP BY major
        """), {"tid": tenant_id, "since": since})
        major_intent = {row.major_name: row.intent_count for row in intent_rows}

        consultation_rows = await db.execute(text("""
            SELECT payload->>'major_name' AS major_name,
                   COUNT(DISTINCT session_id) AS consultation_count
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'recommendation.generated'
              AND created_at >= :since
              AND payload->>'major_name' IS NOT NULL
            GROUP BY payload->>'major_name'
        """), {"tid": tenant_id, "since": since})
        major_consultation = {row.major_name: row.consultation_count for row in consultation_rows}

    all_majors = set()
    all_majors.update(major_feedback.keys())
    all_majors.update(major_intent.keys())
    all_majors.update(major_consultation.keys())

    if not all_majors:
        return {"majors": []}

    max_feedback = max(major_feedback.values()) if major_feedback else 1
    max_intent = max(major_intent.values()) if major_intent else 1
    max_consultation = max(major_consultation.values()) if major_consultation else 1

    majors = []
    for name in all_majors:
        rc = major_feedback.get(name, 0)
        ic = major_intent.get(name, 0)
        cc = major_consultation.get(name, 0)
        heat_score = round(
            (cc / max_consultation * 40) +
            (rc / max_feedback * 35) +
            (ic / max_intent * 25),
            1
        ) if (max_consultation and max_feedback and max_intent) else 0

        majors.append({
            "majorName": name,
            "consultationCount": cc,
            "recommendationCount": rc,
            "intentCount": ic,
            "heatScore": heat_score,
        })

    majors.sort(key=lambda m: m["heatScore"], reverse=True)
    return {"majors": majors}
