"""Emotion timeline — aggregate emotion labels from chat.message_sent over time."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from models import async_session


async def get_emotion_timeline(tenant_id: str, days: int = 30) -> dict:
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = await db.execute(text("""
            SELECT
                created_at::date AS date,
                payload->>'emotion' AS emotion,
                COUNT(*) AS count
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'chat.message_sent'
              AND created_at >= :since
              AND payload->>'emotion' IS NOT NULL
            GROUP BY date, payload->>'emotion'
            ORDER BY date ASC
        """), {"tid": tenant_id, "since": since})

        # Build series per emotion
        emotion_series: dict[str, dict[str, int]] = {}
        all_dates: set[str] = set()
        for row in rows:
            date_str = str(row.date)
            all_dates.add(date_str)
            emotion = row.emotion
            if emotion not in emotion_series:
                emotion_series[emotion] = {}
            emotion_series[emotion][date_str] = row.count

    sorted_dates = sorted(all_dates)
    timeline = []
    for emotion, date_counts in emotion_series.items():
        timeline.append({
            "emotion": emotion,
            "data": [{"date": d, "count": date_counts.get(d, 0)} for d in sorted_dates],
        })

    return {"timeline": timeline, "dates": sorted_dates}
