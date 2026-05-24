"""Hot questions — cluster messages by stage + keyword mentions for Top-10 bar chart."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text


MAJOR_KEYWORDS = [
    "计算机", "软件工程", "人工智能", "数据科学", "电子信息",
    "临床医学", "口腔医学", "护理", "药学",
    "金融", "会计", "工商管理", "经济学",
    "法学", "新闻传播", "英语", "汉语言文学",
    "土木工程", "机械工程", "电气工程", "自动化",
    "数学", "物理", "化学", "生物",
    "建筑", "设计", "艺术", "音乐",
    "师范", "教育", "心理",
    "农学", "环境", "材料",
]


async def get_hot_questions(tenant_id: str, days: int = 30) -> list[dict]:
    from models import async_session
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = await db.execute(text("""
            SELECT payload->>'content' AS content,
                   payload->>'stage' AS stage
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'chat.message_sent'
              AND created_at >= :since
              AND payload->>'content' IS NOT NULL
              AND payload->>'content' != ''
        """), {"tid": tenant_id, "since": since})

        topic_counts: dict[str, int] = {}
        for row in rows:
            text_content = (row.content or "").lower()
            for kw in MAJOR_KEYWORDS:
                if kw.lower() in text_content:
                    topic_counts[kw] = topic_counts.get(kw, 0) + 1

    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    return [{"topic": t, "count": c} for t, c in sorted_topics]
