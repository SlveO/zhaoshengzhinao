"""Profile dashboard — aggregate session_profiles for RIASEC, values, completeness."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
async def get_profile_dashboard(tenant_id: str, days: int = 365) -> dict:
    from models import async_session
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        total = await db.execute(text("""
            SELECT COUNT(*)
            FROM session_profiles
            WHERE tenant_id = :tid
              AND created_at >= :since
        """), {"tid": tenant_id, "since": since})
        total_profiles = total.scalar() or 0

        riasec_rows = await db.execute(text("""
            SELECT dim.key AS dimension,
                   ROUND(AVG((dim.value)::numeric), 1) AS avg_score,
                   COUNT(*) AS count
            FROM session_profiles sp,
                 jsonb_each(sp.profile_json->'riasec') AS dim(key, value)
            WHERE sp.tenant_id = :tid
              AND sp.created_at >= :since
              AND sp.profile_json->'riasec' IS NOT NULL
              AND jsonb_typeof(sp.profile_json->'riasec') = 'object'
            GROUP BY dim.key
            ORDER BY dim.key
        """), {"tid": tenant_id, "since": since})
        riasec_distribution = [
            {"dimension": row.dimension, "avgScore": float(row.avg_score), "count": row.count}
            for row in riasec_rows
        ]

        values_rows = await db.execute(text("""
            SELECT val AS value,
                   COUNT(*) AS count
            FROM session_profiles sp,
                 jsonb_array_elements_text(sp.profile_json->'values') AS val
            WHERE sp.tenant_id = :tid
              AND sp.created_at >= :since
              AND sp.profile_json->'values' IS NOT NULL
              AND jsonb_typeof(sp.profile_json->'values') = 'array'
            GROUP BY val
            ORDER BY count DESC
        """), {"tid": tenant_id, "since": since})
        total_value_occurrences = 0
        values_distribution = []
        for row in values_rows:
            values_distribution.append({"value": row.value, "count": row.count})
            total_value_occurrences += row.count
        for item in values_distribution:
            item["percentage"] = round(item["count"] / total_value_occurrences * 100, 1) if total_value_occurrences else 0
            del item["count"]

        completeness_rows = await db.execute(text("""
            SELECT COALESCE(completeness, 'L1') AS level,
                   COUNT(*) AS count
            FROM session_profiles
            WHERE tenant_id = :tid
              AND created_at >= :since
            GROUP BY completeness
            ORDER BY level
        """), {"tid": tenant_id, "since": since})
        completeness_breakdown = [
            {"level": row.level, "count": row.count}
            for row in completeness_rows
        ]

    return {
        "riasecDistribution": riasec_distribution,
        "valuesDistribution": values_distribution,
        "completenessBreakdown": completeness_breakdown,
        "totalProfiles": total_profiles,
    }
