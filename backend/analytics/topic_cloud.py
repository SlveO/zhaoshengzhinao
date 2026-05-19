"""Topic cloud — jieba segmentation on chat message content, word frequency for wordCloud."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from models import async_session

import jieba

STOP_WORDS = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "什么", "怎么", "如果", "因为", "所以", "但是", "可以", "还是", "这个",
    "那个", "哪个", "觉得", "想", "比较", "可能", "应该", "吧", "吗", "呢",
    "啊", "哦", "嗯", "哈", "呀", "的", "地", "得", "之", "与", "等",
    "及", "或", "对", "把", "被", "让", "向", "从", "以", "为", "而",
    "且", "虽", "但", "却", "所", "如", "若", "则", "能", "会", "将",
    "已", "正", "再", "又", "才", "刚", "就", "便", "即", "只", "可",
    "前", "后", "中", "里", "外", "内", "上", "下", "左", "右", "东",
    "西", "南", "北", "大", "小", "多", "少", "高", "低", "长", "短",
    "去", "来", "做", "干", "搞", "弄", "能", "够", "行", "好", "对",
    "错", "真", "假", "是", "非", "有", "无", "请", "问", "谢", "用",
    "各位", "同学", "大家", "其实", "然后", "而且", "还有", "不过",
    "一下", "一点", "一些", "很多", "非常", "特别", "真的", "还是",
    "怎么样", "什么样", "怎么", "哪", "哪些", "哪里", "什么时候",
})


async def get_topic_cloud(tenant_id: str, days: int = 30) -> list[dict]:
    async with async_session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = await db.execute(text("""
            SELECT payload->>'content' AS content
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'chat.message_sent'
              AND created_at >= :since
              AND payload->>'content' IS NOT NULL
              AND payload->>'content' != ''
        """), {"tid": tenant_id, "since": since})

        word_freq: dict[str, int] = {}
        for row in rows:
            if not row.content:
                continue
            words = jieba.cut(row.content.strip())
            for w in words:
                w = w.strip()
                if len(w) < 2 or w in STOP_WORDS:
                    continue
                word_freq[w] = word_freq.get(w, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
    return [{"word": w, "count": c} for w, c in sorted_words]
