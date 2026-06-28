"""
咨询上下文服务 — 为推荐模块提供咨询会话历史摘要。

当推荐会话通过 context_ref_session_id 绑定了一个咨询会话时，
本服务负责读取该咨询会话的摘要或最近消息，格式化为可插入推荐 prompt 的上下文。

调用方：推荐模块（chat 路由 / recommendation 服务）
"""
import logging
from sqlalchemy import select

from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage

_logger = logging.getLogger(__name__)

# 上下文构建常量
MAX_CONSULT_MESSAGES = 10  # 最多取最近 10 条消息
MAX_SUMMARY_CHARS = 500  # consult_summary 最大字符数
MAX_MESSAGE_CHARS = 200  # 单条消息最大字符数


async def build_consult_context(recommend_session) -> str:
    """为推荐会话构建咨询上下文字符串。

    Args:
        recommend_session: 推荐会话 ORM 对象，需有 context_ref_session_id 字段

    Returns:
        格式化的上下文字符串；若无咨询上下文则返回空串。
        返回值可直接拼接到推荐 prompt 中。
    """
    context_ref = getattr(recommend_session, "context_ref_session_id", None)
    if not context_ref:
        return ""

    try:
        async with async_session() as db:
            # 1. 查询绑定的咨询会话
            consult_result = await db.execute(
                select(ConsultSession).where(ConsultSession.id == context_ref)
            )
            consult_session = consult_result.scalar_one_or_none()

            if not consult_session:
                return ""

            # 2. 优先使用 consult_summary（如果存在且非空）
            summary = getattr(consult_session, "consult_summary", None)
            if summary and summary.strip():
                truncated = summary.strip()[:MAX_SUMMARY_CHARS]
                return f"## 咨询历史摘要\n{truncated}"

            # 3. 无 summary → 查询最近消息
            msg_result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == consult_session.session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(MAX_CONSULT_MESSAGES)
            )
            messages = msg_result.scalars().all()

            if not messages:
                return ""

            # 按时间正序排列（数据库按 desc 取最近 N 条，再反转为正序）
            messages = list(reversed(messages))

            # 格式化消息
            lines = ["## 咨询历史"]
            for msg in messages:
                role_label = _role_label(msg.role)
                content = (msg.content or "")[:MAX_MESSAGE_CHARS]
                lines.append(f"[{role_label}] {content}")

            return "\n".join(lines)

    except Exception as e:
        _logger.warning(
            f"Failed to build consult context for recommend session "
            f"{getattr(recommend_session, 'session_id', '?')}, "
            f"context_ref={context_ref}: {e}"
        )
        return ""


def _role_label(role: str) -> str:
    """将消息角色映射为中文标签。"""
    if role == "user":
        return "学生"
    if role == "assistant":
        return "助手"
    return role
