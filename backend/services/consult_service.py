"""
C端咨询会话服务层。
管理 consult_sessions + chat_messages 的 CRUD。
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage

GUEST_TTL = timedelta(days=1)
REGISTERED_TTL = timedelta(days=30)

# 会话 ID 前缀：用于咨询/推荐模块隔离
CONSULT_SESSION_PREFIX = "sess_consult_"
RECOMMEND_SESSION_PREFIX = "sess_"

_logger = logging.getLogger(__name__)


async def get_or_create_session(
    session_id: str | None,
    tenant_slug: str,
    user_id: uuid.UUID | None = None,
    module_type: str = "recommend",  # "consult" | "recommend"
) -> tuple[ConsultSession, bool]:
    """Return (session, is_new). Expired sessions get a fresh session_id.

    Args:
        module_type: "consult" 创建咨询会话（前缀 sess_consult_），
                     "recommend" 创建推荐会话（前缀 sess_，默认值，保持向后兼容）
    """
    prefix = CONSULT_SESSION_PREFIX if module_type == "consult" else RECOMMEND_SESSION_PREFIX

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

        # 验证 session_id 前缀，不匹配则生成新的（防止跨模块串用）
        # Note: RECOMMEND_SESSION_PREFIX ("sess_") is a substring of
        # CONSULT_SESSION_PREFIX ("sess_consult_"), so we must check
        # the more specific consult prefix first to avoid false matches.
        if session_id:
            if module_type == "consult":
                # Consult sessions must start with "sess_consult_"
                if not session_id.startswith(CONSULT_SESSION_PREFIX):
                    session_id = None
            else:  # recommend
                # Recommend sessions must start with "sess_" AND NOT "sess_consult_"
                if not session_id.startswith(RECOMMEND_SESSION_PREFIX):
                    session_id = None
                elif session_id.startswith(CONSULT_SESSION_PREFIX):
                    # Reject consult-prefixed ids in recommend module
                    session_id = None
        new_id = session_id if session_id else f"{prefix}{uuid.uuid4().hex[:12]}"
        ttl = REGISTERED_TTL if user_id else GUEST_TTL
        expires_at = datetime.now(timezone.utc) + ttl

        # 推荐会话：尝试绑定最近活跃咨询会话（仅注册用户）
        context_ref_session_id = None
        if module_type == "recommend" and user_id:
            try:
                recent_consult_result = await db.execute(
                    select(ConsultSession).where(
                        ConsultSession.user_id == user_id,
                        ConsultSession.tenant_slug == tenant_slug,
                        ConsultSession.session_id.like(f"{CONSULT_SESSION_PREFIX}%"),
                        ConsultSession.consult_started_at.isnot(None),
                    ).order_by(ConsultSession.updated_at.desc()).limit(1)
                )
                recent_consult = recent_consult_result.scalar_one_or_none()
                if recent_consult:
                    context_ref_session_id = recent_consult.id
            except Exception as e:
                _logger.warning(f"Failed to find recent consult session for context_ref: {e}")

        # Snapshot basic info from users table for registered users
        province = ""
        subjects = ""
        score = 0
        rank = None
        if user_id:
            from models.user import User
            user_result = await db.execute(select(User).where(User.id == user_id))
            u = user_result.scalar_one_or_none()
            if u:
                province = u.region or ""
                subjects = u.subjects or ""
                score = u.score or 0
                rank = u.rank

        new_session = ConsultSession(
            session_id=new_id,
            tenant_slug=tenant_slug,
            user_id=user_id,
            province=province,
            subjects=subjects,
            score=score,
            rank=rank,
            expires_at=expires_at,
            context_ref_session_id=context_ref_session_id,
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
            for key in ("province", "subjects", "rank", "score", "intent_majors", "focus_points", "consult_stage"):
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
        # When user sends first message, record consult_started_at
        if role == "user":
            result = await db.execute(
                select(ConsultSession).where(ConsultSession.session_id == session_id)
            )
            session = result.scalar_one_or_none()
            if session and session.consult_started_at is None:
                session.consult_started_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(msg)
        return {"message_id": str(msg.id), "role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()}


async def extract_profile_from_message(user_content: str, ai_response: str, existing_profile: dict) -> dict:
    """Extract intent majors only. Province/subjects/score/rank come from student form."""
    updates = {}
    text = user_content + " " + ai_response
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
    has_any = any([session.province, session.subjects, session.score, session.intent_majors])
    if not has_any:
        return None
    return {
        "province": session.province or None,
        "subjects": session.subjects or None,
        "score": session.score or None,
        "rank": session.rank or None,
        "intent_majors": session.intent_majors or [],
        "focus_points": session.focus_points or [],
    }
