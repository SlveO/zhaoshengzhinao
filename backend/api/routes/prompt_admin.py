"""Admin 提示词管理路由 — CRUD + 版本控制 + 代码同步。

Endpoints:
  GET    /admin/prompts                    — 列出所有 prompt_key
  GET    /admin/prompts/{prompt_key}       — 获取详情（active 内容 + 代码默认值）
  PUT    /admin/prompts/{prompt_key}       — 更新内容（创建新版本，激活，旧版本失效）
  POST   /admin/prompts/sync               — 同步 DB → 代码常量
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from services.prompt_service import CODE_DEFAULTS
from core.tenant_context import get_current_tenant, get_current_tenant_user
from models import async_session, get_db
from models.prompt_template import PromptTemplate
from services.prompt_service import load_prompt
from services.prompt_sync_service import sync_to_code_with_retry

router = APIRouter()
_logger = logging.getLogger(__name__)


class UpdatePromptBody(BaseModel):
    content: str


@router.get("/prompts")
async def list_prompts(
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """列出所有已知 prompt_key 及当前 active 版本信息。"""
    # 查询该租户所有 active 记录
    active_map: dict[str, PromptTemplate] = {}
    try:
        async with async_session() as db:
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.tenant_slug == tenant.slug,
                    PromptTemplate.is_active == True,
                )
            )
            for row in result.scalars().all():
                active_map[row.prompt_key] = row
    except Exception as e:
        _logger.warning(f"list_prompts query failed: {e}")

    prompts = []
    for key in CODE_DEFAULTS.keys():
        active_row = active_map.get(key)
        prompts.append({
            "prompt_key": key,
            "active_version": active_row.version if active_row else None,
            "has_db_record": active_row is not None,
            "is_modified": (active_row is not None and active_row.content != CODE_DEFAULTS[key]),
            "updated_at": active_row.updated_at.isoformat() if active_row and active_row.updated_at else None,
        })

    return {"prompts": prompts}


@router.get("/prompts/{prompt_key}")
async def get_prompt_detail(
    prompt_key: str,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """获取指定 prompt_key 的 active 内容 + 代码默认值。"""
    if prompt_key not in CODE_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Unknown prompt_key: {prompt_key}")

    active_row = None
    try:
        async with async_session() as db:
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.tenant_slug == tenant.slug,
                    PromptTemplate.prompt_key == prompt_key,
                    PromptTemplate.is_active == True,
                ).order_by(PromptTemplate.version.desc())
            )
            active_row = result.scalar_one_or_none()
    except Exception as e:
        _logger.warning(f"get_prompt_detail query failed: {e}")

    code_default = CODE_DEFAULTS[prompt_key]
    content = active_row.content if active_row else code_default

    return {
        "prompt_key": prompt_key,
        "active_version": active_row.version if active_row else None,
        "content": content,
        "code_default": code_default,
        "is_modified": content != code_default,
        "updated_at": active_row.updated_at.isoformat() if active_row and active_row.updated_at else None,
    }


@router.put("/prompts/{prompt_key}")
async def update_prompt(
    prompt_key: str,
    body: UpdatePromptBody,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """更新提示词内容。

    流程：
    1. 校验 prompt_key 合法
    2. 查询当前 max version
    3. 将旧 active 记录置 is_active=False
    4. 创建新版本 (version+1, is_active=True)
    5. 异步同步到代码常量文件（失败不阻塞）
    """
    if prompt_key not in CODE_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Unknown prompt_key: {prompt_key}")

    if not body.content or not body.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")

    user_id = getattr(_user, "user_id", None) or getattr(_user, "id", None)

    try:
        async with async_session() as db:
            # 1. 查询当前 max version
            result = await db.execute(
                select(func.max(PromptTemplate.version)).where(
                    PromptTemplate.tenant_slug == tenant.slug,
                    PromptTemplate.prompt_key == prompt_key,
                )
            )
            max_version = result.scalar_one_or_none() or 0

            # 2. 旧 active 记录置 is_active=False
            await db.execute(
                update(PromptTemplate)
                .where(
                    PromptTemplate.tenant_slug == tenant.slug,
                    PromptTemplate.prompt_key == prompt_key,
                    PromptTemplate.is_active == True,
                )
                .values(is_active=False)
            )

            # 3. 创建新版本
            new_template = PromptTemplate(
                tenant_slug=tenant.slug,
                prompt_key=prompt_key,
                content=body.content,
                version=max_version + 1,
                is_active=True,
                updated_by=user_id,
            )
            db.add(new_template)
            await db.flush()
            await db.refresh(new_template)
            await db.commit()

            # 4. 异步同步到代码常量（失败不阻塞响应）
            try:
                sync_result = await sync_to_code_with_retry(prompt_key, body.content)
                if not sync_result.success:
                    _logger.warning(
                        f"Prompt code sync failed for {prompt_key}: {sync_result.error}"
                    )
            except Exception as e:
                _logger.warning(f"Prompt code sync exception for {prompt_key}: {e}")

            return {
                "prompt_key": prompt_key,
                "version": new_template.version,
                "is_active": True,
                "sync_success": sync_result.success if "sync_result" in dir() else False,
            }
    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"update_prompt failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update prompt")


@router.post("/prompts/sync")
async def sync_prompts(
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """同步所有 prompt_key 的 DB active 内容到代码常量文件。"""
    results = []
    for key in CODE_DEFAULTS.keys():
        try:
            content = await load_prompt(key, tenant.slug)
            if not content:
                results.append({"prompt_key": key, "success": False, "error": "empty content"})
                continue
            sync_result = await sync_to_code_with_retry(key, content)
            results.append({
                "prompt_key": key,
                "success": sync_result.success,
                "attempts": sync_result.attempts,
                "error": sync_result.error,
            })
        except Exception as e:
            results.append({"prompt_key": key, "success": False, "error": str(e)})

    success_count = sum(1 for r in results if r["success"])
    return {
        "total": len(results),
        "success_count": success_count,
        "results": results,
    }
