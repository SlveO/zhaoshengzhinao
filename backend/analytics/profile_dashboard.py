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

        # New stats: monthlyNew, growthRate, todayNewSessions, pendingFollowSessions
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month > 1:
            last_month_start = month_start.replace(month=month_start.month - 1)
        else:
            last_month_start = month_start.replace(year=month_start.year - 1, month=12)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        monthly_new_result = await db.execute(text("""
            SELECT COUNT(*) FROM consult_sessions
            WHERE tenant_slug = (SELECT slug FROM tenants WHERE id = :tid)
              AND consult_started_at >= :ms
        """), {"tid": tenant_id, "ms": month_start})
        monthly_new = monthly_new_result.scalar() or 0

        last_month_new_result = await db.execute(text("""
            SELECT COUNT(*) FROM consult_sessions
            WHERE tenant_slug = (SELECT slug FROM tenants WHERE id = :tid)
              AND consult_started_at >= :lms AND consult_started_at < :ms
        """), {"tid": tenant_id, "lms": last_month_start, "ms": month_start})
        last_month_new = last_month_new_result.scalar() or 0
        growth_rate = round((monthly_new - last_month_new) / last_month_new, 2) if last_month_new else None

        today_new_result = await db.execute(text("""
            SELECT COUNT(*) FROM consult_sessions
            WHERE tenant_slug = (SELECT slug FROM tenants WHERE id = :tid)
              AND consult_started_at >= :ts
        """), {"tid": tenant_id, "ts": today_start})
        today_new_sessions = today_new_result.scalar() or 0

        pending_result = await db.execute(text("""
            SELECT COUNT(*) FROM consult_sessions
            WHERE tenant_slug = (SELECT slug FROM tenants WHERE id = :tid)
              AND follow_status = 'pending'
        """), {"tid": tenant_id})
        pending_follow_sessions = pending_result.scalar() or 0

    return {
        "riasecDistribution": riasec_distribution,
        "valuesDistribution": values_distribution,
        "completenessBreakdown": completeness_breakdown,
        "totalProfiles": total_profiles,
        "monthlyNew": monthly_new,
        "growthRate": growth_rate,
        "todayNewSessions": today_new_sessions,
        "pendingFollowSessions": pending_follow_sessions,
    }
