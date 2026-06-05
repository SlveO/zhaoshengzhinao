"""Distribution API routes — channels, files, tasks, logs."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query

from core.tenant_context import get_current_tenant, get_current_tenant_user
from distribution.schemas import (
    ChannelCreate, ChannelUpdate, ChannelResponse,
    FileUploadResponse, FileDownloadTokenResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    LogResponse, PaginatedResponse,
)
from distribution.security import validate_file_upload, mask_webhook_url
from distribution import service

router = APIRouter()


# ── Channels ─────────────────────────────────────────────────────────

@router.get("/channels")
async def list_channels(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant=Depends(get_current_tenant),
):
    items, total = await service.get_channels(tenant.id, page, page_size)
    return {
        "items": [
            {
                "id": str(ch.id),
                "name": ch.name,
                "channel_type": str(ch.channel_type) if hasattr(ch.channel_type, "value") else ch.channel_type,
                "webhook_url_masked": mask_webhook_url(
                    ch.webhook_url
                ) if ch.webhook_url else "",
                "config": ch.config or {},
                "status": str(ch.status) if hasattr(ch.status, "value") else ch.status,
                "last_test_at": ch.last_test_at,
                "error_message": ch.error_message,
                "created_at": ch.created_at,
            }
            for ch in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/channels", status_code=201)
async def create_channel(
    body: ChannelCreate,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    ch = await service.create_channel(
        tenant.id, body.name, body.channel_type, body.webhook_url, body.config
    )
    return {
        "id": str(ch.id),
        "name": ch.name,
        "channel_type": str(ch.channel_type) if hasattr(ch.channel_type, "value") else ch.channel_type,
        "webhook_url_masked": mask_webhook_url(ch.webhook_url),
        "config": ch.config or {},
        "status": str(ch.status) if hasattr(ch.status, "value") else ch.status,
        "last_test_at": ch.last_test_at,
        "error_message": ch.error_message,
        "created_at": ch.created_at,
    }


@router.get("/channels/{channel_id}")
async def get_channel(
    channel_id: UUID,
    tenant=Depends(get_current_tenant),
):
    ch = await service.get_channel(tenant.id, channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return {
        "id": str(ch.id),
        "name": ch.name,
        "channel_type": str(ch.channel_type) if hasattr(ch.channel_type, "value") else ch.channel_type,
        "webhook_url_masked": mask_webhook_url(ch.webhook_url),
        "config": ch.config or {},
        "status": str(ch.status) if hasattr(ch.status, "value") else ch.status,
        "last_test_at": ch.last_test_at,
        "error_message": ch.error_message,
        "created_at": ch.created_at,
    }


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: UUID,
    body: ChannelUpdate,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    update_data = body.model_dump(exclude_none=True)
    ch = await service.update_channel(tenant.id, channel_id, **update_data)
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return {
        "id": str(ch.id),
        "name": ch.name,
        "channel_type": str(ch.channel_type) if hasattr(ch.channel_type, "value") else ch.channel_type,
        "webhook_url_masked": mask_webhook_url(ch.webhook_url),
        "config": ch.config or {},
        "status": str(ch.status) if hasattr(ch.status, "value") else ch.status,
    }


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: UUID,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    ok = await service.delete_channel(tenant.id, channel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return {"detail": "deleted"}


@router.post("/channels/{channel_id}/test")
async def test_channel(
    channel_id: UUID,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    ch = await service.get_channel(tenant.id, channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    from distribution.security import decrypt_webhook_url
    from distribution.wechat_service import test_webhook

    webhook_url = decrypt_webhook_url(ch.webhook_url)
    result = await test_webhook(webhook_url)
    await service.update_channel_test_result(
        tenant.id, channel_id, result["ok"], result.get("error")
    )
    return result


# ── Files ────────────────────────────────────────────────────────────

@router.post("/files/upload", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    tenant=Depends(get_current_tenant),
    user=Depends(get_current_tenant_user),
):
    content = await file.read()
    error = validate_file_upload(
        file.filename or "unnamed", len(content), file.content_type
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    created_by = user.id if user else None
    df = await service.save_uploaded_file(
        tenant.id,
        file.filename or "unnamed",
        content,
        file.content_type,
        created_by,
    )
    return {
        "id": str(df.id),
        "original_filename": df.original_filename,
        "file_size": df.file_size,
        "mime_type": df.mime_type,
        "created_at": df.created_at,
    }


@router.get("/files")
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant=Depends(get_current_tenant),
):
    items, total = await service.get_files(tenant.id, page, page_size)
    return {
        "items": [
            {
                "id": str(f.id),
                "original_filename": f.original_filename,
                "file_size": f.file_size,
                "mime_type": f.mime_type,
                "created_by": str(f.created_by) if f.created_by else None,
                "created_at": f.created_at,
            }
            for f in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: UUID,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    ok = await service.delete_file(tenant.id, file_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"detail": "deleted"}


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: UUID,
    token: str = Query(...),
):
    """Token-gated file download. No tenant header required."""
    df = await service.validate_access_token(token)
    if not df or df.id != file_id:
        raise HTTPException(status_code=403, detail="无效或过期的访问令牌")

    from fastapi.responses import FileResponse
    file_path = service.get_abs_path(df.stored_path)
    if not __import__("os").path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        file_path,
        filename=df.original_filename,
        media_type=df.mime_type or "application/octet-stream",
    )


# ── Tasks ────────────────────────────────────────────────────────────

@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    tenant=Depends(get_current_tenant),
):
    items, total = await service.get_tasks(tenant.id, page, page_size, status)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/tasks", status_code=201)
async def create_task(
    body: TaskCreate,
    tenant=Depends(get_current_tenant),
    user=Depends(get_current_tenant_user),
):
    try:
        task = await service.create_task(
            tenant.id,
            body.name,
            body.file_id,
            body.channel_id,
            body.schedule_type,
            body.schedule_config,
            body.scheduled_at,
            body.message_text,
            user.id if user else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return service._task_to_dict(task)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: UUID,
    tenant=Depends(get_current_tenant),
):
    task = await service.get_task(tenant.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    update_data = body.model_dump(exclude_none=True)
    task = await service.update_task(tenant.id, task_id, **update_data)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return service._task_to_dict(task)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    ok = await service.delete_task(tenant.id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"detail": "deleted"}


@router.post("/tasks/{task_id}/run")
async def trigger_task(
    task_id: UUID,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    task = await service.get_task(tenant.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    result = await service.execute_task(task_id)
    return result


@router.post("/tasks/{task_id}/pause")
async def pause_task(
    task_id: UUID,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    task = await service.update_task(tenant.id, task_id, status="paused")
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return service._task_to_dict(task)


@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: UUID,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    task = await service.update_task(tenant.id, task_id, status="active")
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return service._task_to_dict(task)


# ── Logs ─────────────────────────────────────────────────────────────

@router.get("/logs")
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_id: UUID | None = Query(None),
    channel_id: UUID | None = Query(None),
    status: str | None = Query(None),
    tenant=Depends(get_current_tenant),
):
    items, total = await service.get_logs(
        tenant.id, page, page_size, task_id, channel_id, status
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
