"""Competitive analysis — compare our profile metrics with market benchmarks and analyze loss."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from models import async_session

RIASEC_LABELS = {
    "R": "动手操作", "I": "研究思考", "A": "艺术创造",
    "S": "帮助他人", "E": "领导说服", "C": "规范有序",
}


async def get_competitive_analysis(tenant_id: str, days: int = 365) -> dict:
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        dimension_rows = await db.execute(text("""
            SELECT dim.key AS dimension,
                   ROUND(AVG((dim.value)::numeric), 1) AS our_score
            FROM session_profiles sp,
                 jsonb_each(sp.profile_json->'riasec') AS dim(key, value)
            WHERE sp.tenant_id = :tid
              AND sp.created_at >= :since
              AND sp.profile_json->'riasec' IS NOT NULL
              AND jsonb_typeof(sp.profile_json->'riasec') = 'object'
            GROUP BY dim.key
            ORDER BY dim.key
        """), {"tid": tenant_id, "since": since})

        comparison_dimensions = []
        for row in dimension_rows:
            label = RIASEC_LABELS.get(row.dimension, row.dimension)
            comparison_dimensions.append({
                "dimension": label,
                "ourScore": float(row.our_score),
                "competitorAvgScore": 5.0,
            })

        loss_rows = await db.execute(text("""
            SELECT COALESCE(payload->>'feedback', 'not_specified') AS reason,
                   COUNT(*) AS count
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'recommendation.feedback'
              AND created_at >= :since
            GROUP BY payload->>'feedback'
        """), {"tid": tenant_id, "since": since})

        total_loss = 0
        loss_items = []
        for row in loss_rows:
            loss_items.append({"reason": row.reason, "count": row.count})
            total_loss += row.count

        loss_analysis = []
        for item in loss_items:
            loss_analysis.append({
                "reason": item["reason"],
                "percentage": round(item["count"] / total_loss * 100, 1) if total_loss else 0,
            })

        if not loss_analysis:
            loss_analysis = [
                {"reason": "缺乏相关专业", "percentage": 0},
                {"reason": "地域偏好不匹配", "percentage": 0},
                {"reason": "分数线不匹配", "percentage": 0},
            ]

    return {
        "comparisonDimensions": comparison_dimensions,
        "lossAnalysis": loss_analysis,
    }
