"""
C端咨询会话服务层。
管理 consult_sessions + chat_messages 的 CRUD。
"""
import uuid
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage

GUEST_TTL = timedelta(days=1)
REGISTERED_TTL = timedelta(days=30)


async def get_or_create_session(
    session_id: str | None, tenant_slug: str, user_id: uuid.UUID | None = None
) -> tuple[ConsultSession, bool]:
    """Return (session, is_new). Expired sessions get a fresh session_id."""
    async with async_session() as db:
        if session_id:
            result = await db.execute(
                select(ConsultSession).where(ConsultSession.session_id == session_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                now = datetime.now(timezone.utc)
                if existing.expires_at is None or existing.expires_at > now:
                    await db.commit()
                    return existing, False
                # Expired: delete old row so we can reuse the session_id
                await db.delete(existing)
                await db.flush()

        # Use provided session_id, generate random only when none given
        new_id = session_id if session_id else f"sess_{uuid.uuid4().hex[:12]}"
        ttl = REGISTERED_TTL if user_id else GUEST_TTL
        expires_at = datetime.now(timezone.utc) + ttl
        new_session = ConsultSession(
            session_id=new_id,
            tenant_slug=tenant_slug,
            user_id=user_id,
            expires_at=expires_at,
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session, True


async def get_session(session_id: str) -> ConsultSession | None:
    async with async_session() as db:
        result = await db.execute(
            select(ConsultSession).where(ConsultSession.session_id == session_id)
        )
        return result.scalar_one_or_none()


async def update_session_profile(session_id: str, updates: dict) -> None:
    """部分更新 session 档案字段。只更新非空值。"""
    async with async_session() as db:
        result = await db.execute(
            select(ConsultSession).where(ConsultSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            for key in ("province", "subject_type", "score", "intent_majors", "focus_points", "consult_stage"):
                if key in updates and updates[key]:
                    setattr(session, key, updates[key])
            await db.commit()


async def get_chat_history(session_id: str, limit: int = 20) -> list[dict]:
    async with async_session() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return [
            {"message_id": str(m.id), "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in result.scalars().all()
        ]


async def save_message(session_id: str, role: str, content: str) -> dict:
    async with async_session() as db:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return {"message_id": str(msg.id), "role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()}


async def extract_profile_from_message(user_content: str, ai_response: str, existing_profile: dict) -> dict:
    """用简单的规则抽取省份、科类、分数、意向专业。返回 {key: value} 更新字典。"""
    updates = {}
    text = user_content + " " + ai_response
    if not existing_profile.get("province"):
        for prov in ["广东", "北京", "上海", "浙江", "江苏", "四川", "湖北", "湖南", "山东", "河南"]:
            if prov in text:
                updates["province"] = prov
                break
    if not existing_profile.get("subject_type"):
        if "物理" in text or "理科" in text:
            updates["subject_type"] = "物理类"
        elif "历史" in text or "文科" in text:
            updates["subject_type"] = "历史类"
    if not existing_profile.get("score"):
        m = re.search(r"(\d{3})\s*分", text)
        if m:
            updates["score"] = int(m.group(1))
    if not existing_profile.get("intent_majors"):
        major_keywords = [
            "计算机", "人工智能", "软件工程", "数据科学", "网络安全", "大数据",
            "电子信息", "通信工程", "自动化", "电气工程", "微电子",
            "机械", "土木", "建筑", "材料", "环境",
            "临床医学", "口腔医学", "药学", "护理",
            "法学", "经济学", "金融", "会计", "工商管理", "国际贸易",
            "数学", "物理", "化学", "生物", "地理",
            "中文", "英语", "日语", "新闻", "历史", "哲学",
            "师范", "教育", "心理", "体育",
        ]
        found = []
        for kw in major_keywords:
            if kw in text:
                found.append(kw)
        if found:
            updates["intent_majors"] = found[:5]
    return updates


def build_profile_summary(session: ConsultSession) -> dict | None:
    has_any = any([session.province, session.subject_type, session.score, session.intent_majors])
    if not has_any:
        return None
    return {
        "province": session.province or None,
        "subject_type": session.subject_type or None,
        "score": session.score or None,
        "intent_majors": session.intent_majors or [],
        "focus_points": session.focus_points or [],
    }
