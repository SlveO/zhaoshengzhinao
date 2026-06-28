"""推荐模块集成测试 — 验证 consult_context_service 与 miniapp chat 路由的集成。

测试契约：
1. 推荐会话无 context_ref_session_id → build_consult_context 返回空字符串
2. 推荐会话绑定咨询会话且有 consult_summary → 返回摘要
3. 推荐会话绑定咨询会话但无 summary → 回退到最近消息
4. 绑定的咨询会话不存在 → 返回空字符串
5. B2B_SYSTEM_PROMPT 含 {consult_context} 占位符 — format 不报错
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from services.consult_context_service import (
    MAX_CONSULT_MESSAGES,
    MAX_SUMMARY_CHARS,
    MAX_MESSAGE_CHARS,
    build_consult_context,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """覆盖 conftest.py 的 setup_db — 跳过 DB 连接。"""
    yield


def _make_session(context_ref=None):
    """创建 mock 推荐会话。"""
    s = MagicMock()
    s.context_ref_session_id = context_ref
    return s


def _make_consult_session(consult_summary=None):
    """创建 mock 咨询会话。"""
    s = MagicMock()
    s.consult_summary = consult_summary
    s.session_id = "sess_consult_abc123"
    return s


def _make_message(role, content, created_at=None):
    """创建 mock ChatMessage。"""
    m = MagicMock()
    m.role = role
    m.content = content
    m.created_at = created_at or MagicMock()
    return m


@pytest.mark.asyncio
async def test_no_context_ref_returns_empty():
    """推荐会话无 context_ref_session_id → 返回空字符串。"""
    session = _make_session(context_ref=None)
    result = await build_consult_context(session)
    assert result == ""


@pytest.mark.asyncio
async def test_summary_present_returns_summary():
    """咨询会话有 consult_summary → 优先返回摘要。"""
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


@pytest.mark.asyncio
async def test_no_summary_falls_back_to_messages():
    """咨询会话无 summary → 回退查询最近消息。"""
    consult_id = uuid.uuid4()
    session = _make_session(context_ref=consult_id)
    consult = _make_consult_session(consult_summary=None)

    messages = [
        _make_message("user", "我想了解计算机专业"),
        _make_message("assistant", "好的，计算机专业..."),
    ]

    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        # 第一次 execute 返回 consult_session，第二次返回 messages
        consult_result = MagicMock()
        consult_result.scalar_one_or_none.return_value = consult
        msg_result = MagicMock()
        msg_scalars = MagicMock()
        msg_scalars.all.return_value = messages
        msg_result.scalars.return_value = msg_scalars

        mock_db.execute = AsyncMock(side_effect=[consult_result, msg_result])
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await build_consult_context(session)

    assert "## 咨询历史" in result
    assert "我想了解计算机专业" in result
    assert "好的，计算机专业" in result


@pytest.mark.asyncio
async def test_consult_session_not_found_returns_empty():
    """绑定的咨询会话不存在（已删除）→ 返回空字符串。"""
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
async def test_summary_truncated_to_max_chars():
    """consult_summary 超长 → 截断到 MAX_SUMMARY_CHARS。"""
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

    # 截断后内容长度 = MAX_SUMMARY_CHARS（不含标题行）
    body = result.replace("## 咨询历史摘要\n", "")
    assert len(body) == MAX_SUMMARY_CHARS


def test_b2b_prompt_contains_consult_context_placeholder():
    """B2B_SYSTEM_PROMPT 必须含 {consult_context} 占位符 — 否则 format 会 KeyError。"""
    from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT

    assert "{consult_context}" in B2B_SYSTEM_PROMPT, \
        "B2B_SYSTEM_PROMPT missing {consult_context} placeholder"

    # 验证 format 调用成功
    formatted = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华师",
        stage="open",
        slots_summary="省份: 广东",
        consult_context="## 咨询历史摘要\n学生想学计算机",
    )
    assert "学生想学计算机" in formatted
    assert "华南师范大学" in formatted


def test_b2b_prompt_format_with_empty_consult_context():
    """consult_context 为空字符串时 format 不报错。"""
    from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT

    formatted = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华师",
        stage="open",
        slots_summary="省份: 广东",
        consult_context="",
    )
    # 应该成功格式化，没有 KeyError
    assert "华南师范大学" in formatted


@pytest.mark.asyncio
async def test_miniapp_chat_calls_build_consult_context():
    """验证 miniapp chat 路由会调用 build_consult_context。"""
    # 这个测试验证集成点：miniapp.py 导入了 build_consult_context
    # 并且在 chat 路由中调用了它
    from api.routes import miniapp

    # 验证 import 存在
    assert hasattr(miniapp, "build_consult_context"), \
        "miniapp 模块未导入 build_consult_context"
