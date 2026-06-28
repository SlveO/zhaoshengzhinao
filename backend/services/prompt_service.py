"""提示词加载服务：DB 优先 → 代码常量回退。"""
import logging

from sqlalchemy import select
from models import async_session
from models.prompt_template import PromptTemplate
from agents.conversation.prompts_consult import CODE_DEFAULTS as _CONSULT_DEFAULTS
from agents.conversation.prompts_consult import PROMPT_FILE_MAP as _CONSULT_MAP
from agents.conversation.prompts_b2b import CODE_DEFAULTS as _B2B_DEFAULTS
from agents.conversation.prompts_b2b import PROMPT_FILE_MAP as _B2B_MAP

# 合并 consult + b2b 两个模块的映射表，单一来源供 prompt_admin / prompt_sync_service / lifespan 使用
CODE_DEFAULTS = {**_CONSULT_DEFAULTS, **_B2B_DEFAULTS}
PROMPT_FILE_MAP = {**_CONSULT_MAP, **_B2B_MAP}

_logger = logging.getLogger(__name__)


async def load_prompt(prompt_key: str, tenant_slug: str = "scnu") -> str:
    """加载提示词。优先从 DB active 记录读取，失败回退代码默认值。

    Args:
        prompt_key: consult_system / consult_intent / consult_degraded / ...
        tenant_slug: 租户 slug，默认 scnu

    Returns:
        提示词内容字符串；DB 无记录且无代码默认值时返回空串。
    """
    try:
        async with async_session() as db:
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.tenant_slug == tenant_slug,
                    PromptTemplate.prompt_key == prompt_key,
                    PromptTemplate.is_active == True,
                ).order_by(PromptTemplate.version.desc())
            )
            row = result.scalar_one_or_none()
            if row:
                return row.content
    except Exception as e:
        _logger.warning(f"Failed to load prompt {prompt_key} from DB: {e}")

    return CODE_DEFAULTS.get(prompt_key, "")


async def get_active_version(prompt_key: str, tenant_slug: str = "scnu") -> int | None:
    """获取当前 active 版本号，无记录返回 None。"""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.tenant_slug == tenant_slug,
                    PromptTemplate.prompt_key == prompt_key,
                    PromptTemplate.is_active == True,
                ).order_by(PromptTemplate.version.desc())
            )
            row = result.scalar_one_or_none()
            return row.version if row else None
    except Exception:
        return None
