"""提示词代码常量文件同步服务（双写机制）。

DB 是主存储，代码常量同步失败不阻塞 DB 保存。
通过 sync_to_code_with_retry 提供 3 次重试 + 指数退避。
"""
import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from services.prompt_service import PROMPT_FILE_MAP

_logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    success: bool
    attempts: int
    error: str | None = None


async def sync_to_code_with_retry(prompt_key: str, content: str) -> SyncResult:
    """同步提示词到代码常量文件，3 次重试，指数退避 1s/2s/4s。

    Args:
        prompt_key: 如 "consult_system"
        content: 新的提示词内容

    Returns:
        SyncResult(success, attempts, error)
    """
    if prompt_key not in PROMPT_FILE_MAP:
        return SyncResult(success=False, attempts=0, error=f"Unknown prompt_key: {prompt_key}")

    file_path_str, const_name = PROMPT_FILE_MAP[prompt_key]
    last_error = ""

    for attempt in range(3):
        try:
            await _sync_to_code_file(file_path_str, const_name, content)
            return SyncResult(success=True, attempts=attempt + 1)
        except Exception as e:
            last_error = str(e)
            _logger.warning(f"Prompt sync attempt {attempt + 1} failed for {prompt_key}: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    return SyncResult(success=False, attempts=3, error=last_error)


async def _sync_to_code_file(file_path_str: str, const_name: str, content: str) -> None:
    """用正则替换 .py 文件中的常量定义。

    匹配模式：{const_name} = \"\"\"...\"\"\"
    替换为：{const_name} = \"\"\"{content}\"\"\"
    """
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    original = await asyncio.to_thread(file_path.read_text, "utf-8")

    pattern = re.compile(
        rf'({re.escape(const_name)}\s*=\s*""")([\s\S]*?)(""")',
        re.MULTILINE
    )

    if not pattern.search(original):
        raise ValueError(f"Constant {const_name} not found in {file_path}")

    replacement = lambda m: f'{m.group(1)}{content}{m.group(3)}'
    updated = pattern.sub(replacement, original, count=1)
    await asyncio.to_thread(file_path.write_text, updated, "utf-8")
