"""
C端咨询会话服务层。
管理 consult_sessions + chat_messages 的 CRUD。
"""
import uuid
import re
from sqlalchemy import select
from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage


async def get_or_create_session(session_id: str | None, tenant_slug: str) -> tuple[ConsultSession, bool]:
    """返回 (session, is_new)。session_id 为 None 时创建新会话。"""
    async with async_session() as db:
        if session_id:
            result = await db.execute(
                select(ConsultSession).where(ConsultSession.session_id == session_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                await db.commit()
                return existing, False

        new_id = session_id if session_id else f"sess_{uuid.uuid4().hex[:12]}"
        new_session = ConsultSession(
            session_id=new_id,
            tenant_slug=tenant_slug,
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
