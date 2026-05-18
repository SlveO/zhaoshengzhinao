"""Region distribution — aggregate session profile region preferences."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from models import async_session


async def get_region_distribution(tenant_id: str, days: int = 365) -> dict:
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        rows = await db.execute(text("""
            SELECT pref AS province,
                   pref AS city,
                   COUNT(*) AS student_count,
                   ROUND(AVG(COALESCE((sp.profile_json->>'score')::int, 0)), 0) AS avg_score
            FROM session_profiles sp,
                 jsonb_array_elements_text(sp.profile_json->'region_pref') AS pref
            WHERE sp.tenant_id = :tid
              AND sp.created_at >= :since
              AND sp.profile_json->'region_pref' IS NOT NULL
              AND jsonb_typeof(sp.profile_json->'region_pref') = 'array'
            GROUP BY pref
            ORDER BY student_count DESC
        """), {"tid": tenant_id, "since": since})

        regions = [
            {
                "province": row.province,
                "city": row.city,
                "studentCount": row.student_count,
                "avgScore": int(row.avg_score),
            }
            for row in rows
        ]

    return {"regions": regions}
