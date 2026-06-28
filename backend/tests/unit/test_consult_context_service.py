"""consult_context_service 单测 — 推荐模块访问咨询会话历史的上下文构建。

测试契约：
1. recommend 会话无 context_ref_session_id → 返回空串
2. context_ref 指向的咨询会话不存在 → 返回空串
3. 咨询会话存在但无消息 → 返回空串
4. 咨询会话有消息 → 返回格式化的上下文字符串
5. 消息超过 MAX_MESSAGES 时截断到最近 N 条
6. consult_summary 存在时优先使用 summary
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from services.consult_context_service import (
    build_consult_context,
    MAX_CONSULT_MESSAGES,
    MAX_SUMMARY_CHARS,
)


# 纯单元测试（mock async_session）— 覆盖 conftest.py 的 autouse setup_db，避免连真实 DB
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _make_session(session_id="sess_consult_abc", context_ref=None, consult_summary=None):
    """构造 mock 推荐会话。"""
    session = MagicMock()
    session.id = uuid.uuid4()
    session.session_id = session_id
    session.tenant_slug = "scnu"
    session.context_ref_session_id = context_ref
    session.consult_summary = consult_summary
    return session


def _make_consult_session(consult_summary=None):
    """构造 mock 咨询会话。"""
    consult = MagicMock()
    consult.id = uuid.uuid4()
    consult.consult_summary = consult_summary
    return consult


def _make_msg(role, content):
    msg = MagicMock()
    msg.role = role
    msg.content = content
    return msg


@pytest.mark.asyncio
async def test_returns_empty_when_no_context_ref():
    """推荐会话未绑定咨询会话 → 返回空串。"""
    session = _make_session(context_ref=None)

    with patch("services.consult_context_service.async_session") as mock_session:
        result = await build_consult_context(session)

        assert result == ""
        # Should not even hit DB
        mock_session.assert_not_called()


@pytest.mark.asyncio
async def test_returns_empty_when_consult_session_not_found():
    """context_ref 指向的咨询会话不存在 → 返回空串。"""
    consult_id = uuid.uuid4()
    session = _make_session(context_ref=consult_id)

    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await build_consult_context(session)

        assert result == ""


@pytest.mark.asyncio
async def test_uses_consult_summary_when_present_and_nonempty():
    """咨询会话有 consult_summary → 优先返回 summary，不查询消息。"""
    consult_id = uuid.uuid4()
    session = _make_session(context_ref=consult_id)
    consult = _make_consult_session(consult_summary="学生想学计算机，关注就业，分数620")

    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = consult
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await build_consult_context(session)

        assert "学生想学计算机" in result
        assert "## 咨询历史摘要" in result
        # Only one DB call (session lookup), no second call for messages
        assert mock_db.execute.call_count == 1


@pytest.mark.asyncio
async def test_returns_empty_when_no_summary_and_no_messages():
    """咨询会话无 summary 也无消息 → 返回空串。"""
    consult_id = uuid.uuid4()
    session = _make_session(context_ref=consult_id)
    consult = _make_consult_session(consult_summary=None)

    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        # First call: consult session lookup → returns consult
        # Second call: messages lookup → returns empty list
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = consult

        msg_scalars = MagicMock()
        msg_scalars.all.return_value = []
        msg_result = MagicMock()
        msg_result.scalars.return_value = msg_scalars

        mock_db.execute = AsyncMock(side_effect=[session_result, msg_result])
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await build_consult_context(session)

        assert result == ""


@pytest.mark.asyncio
async def test_formats_messages_when_no_summary():
    """无 summary 但有消息 → 返回格式化的咨询历史。"""
    consult_id = uuid.uuid4()
    consult_session_id_str = "sess_consult_xyz"
    session = _make_session(context_ref=consult_id)
    consult = _make_consult_session(consult_summary=None)
    # Set session_id on consult for message query
    consult.session_id = consult_session_id_str

    messages = [
        _make_msg("user", "我想学计算机"),
        _make_msg("assistant", "好的，您的分数是多少？"),
        _make_msg("user", "620分"),
    ]

    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = consult

        msg_scalars = MagicMock()
        msg_scalars.all.return_value = messages
        msg_result = MagicMock()
        msg_result.scalars.return_value = msg_scalars

        mock_db.execute = AsyncMock(side_effect=[session_result, msg_result])
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await build_consult_context(session)

        assert "## 咨询历史" in result
        assert "我想学计算机" in result
        assert "620分" in result
        assert "[学生]" in result or "[用户]" in result
        assert "[助手]" in result or "[AI]" in result


@pytest.mark.asyncio
async def test_truncates_to_max_messages():
    """消息超过 MAX_CONSULT_MESSAGES 时截断到最近 N 条。

    Note: SQL 查询使用 .limit(MAX_CONSULT_MESSAGES)，所以 mock 应模拟
    DB 只返回最近 N 条消息的行为。service 层不做额外截断（依赖 SQL limit）。
    """
    consult_id = uuid.uuid4()
    session = _make_session(context_ref=consult_id)
    consult = _make_consult_session(consult_summary=None)
    consult.session_id = "sess_consult_xyz"

    # 模拟 SQL .limit(MAX_CONSULT_MESSAGES) + .order_by(desc) 的行为：
    # 总共 15 条消息（0..14），DB 只返回最近 10 条（5..14），按 desc 排序
    all_messages = [_make_msg("user", f"消息{i}") for i in range(MAX_CONSULT_MESSAGES + 5)]
    # SQL order_by(desc) + limit(10) → 返回 [14, 13, 12, ..., 5]
    db_returned = list(reversed(all_messages[-MAX_CONSULT_MESSAGES:]))  # [14, 13, ..., 5]

    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = consult

        msg_scalars = MagicMock()
        msg_scalars.all.return_value = db_returned
        msg_result = MagicMock()
        msg_result.scalars.return_value = msg_scalars

        mock_db.execute = AsyncMock(side_effect=[session_result, msg_result])
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await build_consult_context(session)

        # 最近的消息（14）应该保留，最早的消息（0-4）应该被截断
        assert f"消息{MAX_CONSULT_MESSAGES + 4}" in result  # Last message kept
        assert f"消息0" not in result  # First message truncated
        assert f"消息4" not in result  # 5th message truncated (boundary)


@pytest.mark.asyncio
async def test_truncates_overlong_summary():
    """consult_summary 超过 MAX_SUMMARY_CHARS 时截断。"""
    consult_id = uuid.uuid4()
    session = _make_session(context_ref=consult_id)
    long_summary = "A" * (MAX_SUMMARY_CHARS + 100)
    consult = _make_consult_session(consult_summary=long_summary)

    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = consult
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await build_consult_context(session)

        # The summary should be truncated to MAX_SUMMARY_CHARS
        # Count only the A's in the result (excluding the header)
        a_count = result.count("A")
        assert a_count == MAX_SUMMARY_CHARS
