"""prompt_service 单测 — 仅依赖 PromptTemplate ORM 与代码常量回退。

测试契约：
1. DB 中无记录时，load_prompt 返回代码默认值
2. DB 中有 active 记录时，返回 DB 内容
3. 无效 prompt_key（不在 CODE_DEFAULTS 且 DB 也无）返回空串
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from agents.conversation.prompts_consult import CODE_DEFAULTS


# 纯单元测试（mock async_session）— 覆盖 conftest.py 的 autouse setup_db，避免连真实 DB
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.mark.asyncio
async def test_load_prompt_fallback_to_code_default():
    """DB 无记录时回退代码常量。"""
    from services.prompt_service import load_prompt
    with patch("services.prompt_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await load_prompt("consult_system", "scnu")
        assert result == CODE_DEFAULTS["consult_system"]


@pytest.mark.asyncio
async def test_load_prompt_returns_db_content_when_present():
    """DB 有 active 记录时返回 DB 内容。"""
    from services.prompt_service import load_prompt
    db_content = "自定义咨询提示词内容"
    with patch("services.prompt_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_row = MagicMock()
        mock_row.content = db_content
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await load_prompt("consult_system", "scnu")
        assert result == db_content


@pytest.mark.asyncio
async def test_load_prompt_invalid_key_returns_empty_string():
    """无效 prompt_key（不在 CODE_DEFAULTS 且 DB 也无）返回空串。"""
    from services.prompt_service import load_prompt
    with patch("services.prompt_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await load_prompt("nonexistent_key", "scnu")
        assert result == ""
