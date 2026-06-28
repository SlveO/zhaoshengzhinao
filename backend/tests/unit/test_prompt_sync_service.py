"""prompt_sync_service 单测 — 代码常量文件同步。

测试契约：
1. sync_to_code_with_retry 成功时返回 SyncResult(success=True)
2. 文件写入失败时重试 3 次
3. 正则替换保留常量名，仅替换内容
"""
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


# 纯单元测试（mock 文件系统）— 覆盖 conftest.py 的 autouse setup_db，避免连真实 DB
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.mark.asyncio
async def test_sync_success_returns_success_result(tmp_path):
    """成功同步返回 success=True。"""
    from services.prompt_sync_service import sync_to_code_with_retry
    test_file = tmp_path / "prompts_consult.py"
    test_file.write_text(
        'CONSULT_SYSTEM_PROMPT = """旧内容"""\n',
        encoding="utf-8",
    )

    new_content = "新内容"
    with patch("services.prompt_sync_service.PROMPT_FILE_MAP", {
        "consult_system": (str(test_file), "CONSULT_SYSTEM_PROMPT"),
    }):
        result = await sync_to_code_with_retry("consult_system", new_content)

    assert result.success is True
    assert "新内容" in test_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_sync_failure_returns_failure_result_after_retries():
    """文件不存在时返回 success=False（重试 3 次）。"""
    from services.prompt_sync_service import sync_to_code_with_retry
    with patch("services.prompt_sync_service.PROMPT_FILE_MAP", {
        "consult_system": ("/nonexistent/path/file.py", "CONSULT_SYSTEM_PROMPT"),
    }):
        with patch("services.prompt_sync_service.asyncio.sleep", new=AsyncMock()):
            result = await sync_to_code_with_retry("consult_system", "内容")

    assert result.success is False
    assert result.attempts == 3


@pytest.mark.asyncio
async def test_sync_replaces_only_constant_content(tmp_path):
    """正则替换仅替换常量内容，保留常量名与三引号结构。"""
    from services.prompt_sync_service import sync_to_code_with_retry
    test_file = tmp_path / "prompts_consult.py"
    original = (
        'OTHER_CONST = "x"\n'
        '\n'
        'CONSULT_SYSTEM_PROMPT = """旧内容\n多行\n"""\n'
        '\n'
        'ANOTHER = 1\n'
    )
    test_file.write_text(original, encoding="utf-8")

    with patch("services.prompt_sync_service.PROMPT_FILE_MAP", {
        "consult_system": (str(test_file), "CONSULT_SYSTEM_PROMPT"),
    }):
        result = await sync_to_code_with_retry("consult_system", "新内容")

    content = test_file.read_text(encoding="utf-8")
    assert result.success is True
    assert 'OTHER_CONST = "x"' in content
    assert "ANOTHER = 1" in content
    assert 'CONSULT_SYSTEM_PROMPT = """新内容"""' in content
