"""Trigger-based LLM consult summary generation."""
import asyncio
import logging

from sqlalchemy import select, func
from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage


async def _count_user_messages(session_id: str) -> int:
    async with async_session() as db:
        result = await db.execute(
            select(func.count()).select_from(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.role == "user")
        )
        return result.scalar() or 0


async def _get_recent_messages(session_id: str, limit: int = 8) -> list[dict]:
    async with async_session() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        msgs = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in msgs]


async def generate_summary(session_id: str) -> str:
    """Generate a 30-char summary. Falls back to first user message truncated."""
    msgs = await _get_recent_messages(session_id, limit=8)
    if not msgs:
        return ""

    user_msgs = [m for m in msgs if m["role"] == "user"]
    if not user_msgs:
        return ""

    fallback = user_msgs[0]["content"][:30]

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        from config import settings

        llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.3,
        )
        conversation_text = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
        sys = SystemMessage(content="你是咨询摘要助手。用30字以内总结学生本次咨询的核心问题，例如：'计算机专业就业前景与转专业政策咨询'。直接输出总结内容，不加任何前缀。")
        hum = HumanMessage(content=f"对话内容：\n{conversation_text}\n\n请总结：")
        resp = await llm.ainvoke([sys, hum])
        summary = (resp.content or "").strip()[:30]
        return summary or fallback
    except Exception as e:
        logging.warning(f"Summary LLM failed for session={session_id}: {e}")
        return fallback


async def maybe_generate_summary(session_id: str) -> None:
    """Trigger summary generation based on message count.

    First time: user_msgs >= 4 and consult_summary is None.
    Refresh: regenerate every 2 new messages after the first summary.
    """
    async with async_session() as db:
        result = await db.execute(
            select(ConsultSession).where(ConsultSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return

        user_count = await _count_user_messages(session_id)
        if user_count < 4:
            return

        if session.consult_summary is None:
            should_gen = True
        elif user_count % 2 == 0:
            should_gen = True
        else:
            should_gen = False

        if not should_gen:
            return

        summary = await generate_summary(session_id)
        if summary:
            session.consult_summary = summary
            await db.commit()
            logging.info(f"Summary updated for session={session_id}: {summary}")
