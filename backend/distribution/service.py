"""Business logic for distribution module — channels, files, tasks, logs."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, and_, or_

from models import async_session
from distribution.models import (
    DistributionChannel,
    DistributionFile,
    DistributionTask,
    DistributionLog,
    DistributionFileAccessToken,
)
from distribution.security import (
    encrypt_webhook_url,
    decrypt_webhook_url,
    mask_webhook_url,
    generate_access_token,
    validate_file_upload,
    compute_file_hash,
)
from config import settings


# ── Channel CRUD ─────────────────────────────────────────────────────

async def get_channels(tenant_id: uuid.UUID, page: int = 1, page_size: int = 20
                       ) -> tuple[list[DistributionChannel], int]:
    async with async_session() as db:
        base = select(DistributionChannel).where(
            DistributionChannel.tenant_id == tenant_id,
            DistributionChannel.deleted_at.is_(None),
        )
        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            base.order_by(DistributionChannel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total


async def create_channel(tenant_id: uuid.UUID, name: str, channel_type: str,
                         webhook_url: str, config: dict = None) -> DistributionChannel:
    async with async_session() as db:
        channel = DistributionChannel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            channel_type=channel_type,
            webhook_url=encrypt_webhook_url(webhook_url),
            config=config or {},
        )
        db.add(channel)
        await db.commit()
        await db.refresh(channel)
        return channel


async def get_channel(tenant_id: uuid.UUID, channel_id: uuid.UUID
                      ) -> DistributionChannel | None:
    async with async_session() as db:
        result = await db.execute(
            select(DistributionChannel).where(
                DistributionChannel.id == channel_id,
                DistributionChannel.tenant_id == tenant_id,
                DistributionChannel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()


async def update_channel(tenant_id: uuid.UUID, channel_id: uuid.UUID,
                         **fields) -> DistributionChannel | None:
    async with async_session() as db:
        channel = await db.get(DistributionChannel, channel_id)
        if not channel or channel.tenant_id != tenant_id or channel.deleted_at:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(channel, key):
                if key == "webhook_url":
                    value = encrypt_webhook_url(value)
                setattr(channel, key, value)
        channel.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(channel)
        return channel


async def delete_channel(tenant_id: uuid.UUID, channel_id: uuid.UUID) -> bool:
    async with async_session() as db:
        channel = await db.get(DistributionChannel, channel_id)
        if not channel or channel.tenant_id != tenant_id:
            return False
        channel.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        return True


async def update_channel_test_result(tenant_id: uuid.UUID, channel_id: uuid.UUID,
                                     ok: bool, error_msg: str | None = None):
    async with async_session() as db:
        channel = await db.get(DistributionChannel, channel_id)
        if not channel or channel.tenant_id != tenant_id:
            return
        channel.last_test_at = datetime.now(timezone.utc)
        if ok:
            channel.status = "active"
            channel.error_message = None
        else:
            channel.status = "error"
            channel.error_message = error_msg
        await db.commit()


# ── File CRUD ────────────────────────────────────────────────────────

async def save_uploaded_file(tenant_id: uuid.UUID, original_filename: str,
                             content: bytes, mime_type: str | None = None,
                             created_by: uuid.UUID | None = None) -> DistributionFile:
    file_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    # Build tenant-isolated path: file_store/{tenant_id}/{YYYY}/{MM}/{uuid}_{filename}
    rel_dir = os.path.join(
        str(tenant_id),
        now.strftime("%Y"),
        now.strftime("%m"),
    )
    abs_dir = os.path.join(settings.file_store_dir, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    stored_filename = f"{file_id}_{original_filename}"
    abs_path = os.path.join(abs_dir, stored_filename)

    with open(abs_path, "wb") as f:
        f.write(content)

    file_hash = compute_file_hash(abs_path)
    rel_path = os.path.join(rel_dir, stored_filename)

    async with async_session() as db:
        df = DistributionFile(
            id=file_id,
            tenant_id=tenant_id,
            original_filename=original_filename,
            stored_path=rel_path,
            file_size=len(content),
            mime_type=mime_type,
            file_hash=file_hash,
            created_by=created_by,
        )
        db.add(df)
        await db.commit()
        await db.refresh(df)
        return df


def get_abs_path(stored_path: str) -> str:
    """Convert a relative stored_path to an absolute filesystem path."""
    return os.path.join(settings.file_store_dir, stored_path)


async def get_files(tenant_id: uuid.UUID, page: int = 1, page_size: int = 20
                    ) -> tuple[list[DistributionFile], int]:
    async with async_session() as db:
        base = select(DistributionFile).where(
            DistributionFile.tenant_id == tenant_id,
            DistributionFile.deleted_at.is_(None),
        )
        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            base.order_by(DistributionFile.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total


async def get_file(tenant_id: uuid.UUID, file_id: uuid.UUID
                   ) -> DistributionFile | None:
    async with async_session() as db:
        result = await db.execute(
            select(DistributionFile).where(
                DistributionFile.id == file_id,
                DistributionFile.tenant_id == tenant_id,
                DistributionFile.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()


async def delete_file(tenant_id: uuid.UUID, file_id: uuid.UUID) -> bool:
    async with async_session() as db:
        df = await db.get(DistributionFile, file_id)
        if not df or df.tenant_id != tenant_id:
            return False
        df.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        # Delete from disk
        abs_path = get_abs_path(df.stored_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
        return True


# ── Access Token ─────────────────────────────────────────────────────

async def create_access_token(file_id: uuid.UUID, channel_id: uuid.UUID | None = None,
                              expires_in_hours: int = 24,
                              max_access: int = 1) -> DistributionFileAccessToken:
    async with async_session() as db:
        token = DistributionFileAccessToken(
            id=uuid.uuid4(),
            file_id=file_id,
            token=generate_access_token(file_id, channel_id, expires_in_hours),
            channel_id=channel_id,
            expires_at=datetime.now(timezone.utc) + __import__("datetime").timedelta(hours=expires_in_hours),
            max_access=max_access,
        )
        db.add(token)
        await db.commit()
        await db.refresh(token)
        return token


async def validate_access_token(token_str: str) -> DistributionFile | None:
    """Validate an access token and return the associated file."""
    from datetime import datetime as dt, timezone as tz, timedelta
    async with async_session() as db:
        result = await db.execute(
            select(DistributionFileAccessToken).where(
                DistributionFileAccessToken.token == token_str,
            )
        )
        token = result.scalar_one_or_none()
        if not token:
            return None
        if token.expires_at < datetime.now(timezone.utc):
            return None
        if token.access_count >= token.max_access:
            return None
        token.access_count += 1
        # Get the file
        file_result = await db.execute(
            select(DistributionFile).where(
                DistributionFile.id == token.file_id,
                DistributionFile.deleted_at.is_(None),
            )
        )
        df = file_result.scalar_one_or_none()
        await db.commit()
        return df


# ── Task CRUD ────────────────────────────────────────────────────────

async def get_tasks(tenant_id: uuid.UUID, page: int = 1, page_size: int = 20,
                    status: str | None = None
                    ) -> tuple[list[dict], int]:
    async with async_session() as db:
        base = select(DistributionTask).where(
            DistributionTask.tenant_id == tenant_id,
            DistributionTask.deleted_at.is_(None),
        )
        if status:
            base = base.where(DistributionTask.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            base.order_by(DistributionTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        tasks = list(result.scalars().all())
        # Enrich with joined names
        return [_task_to_dict(t) for t in tasks], total


def _task_to_dict(t: DistributionTask) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "file_id": str(t.file_id),
        "channel_id": str(t.channel_id),
        "schedule_type": str(t.schedule_type) if hasattr(t.schedule_type, "value") else t.schedule_type,
        "schedule_config": t.schedule_config or {},
        "scheduled_at": t.scheduled_at,
        "status": str(t.status) if hasattr(t.status, "value") else t.status,
        "message_text": t.message_text,
        "created_at": t.created_at,
        "file_name": t.file.original_filename if t.file else None,
        "channel_name": t.channel.name if t.channel else None,
    }


async def create_task(tenant_id: uuid.UUID, name: str, file_id: uuid.UUID,
                      channel_id: uuid.UUID, schedule_type: str = "once",
                      schedule_config: dict = None, scheduled_at: datetime = None,
                      message_text: str | None = None,
                      created_by: uuid.UUID | None = None) -> DistributionTask:
    async with async_session() as db:
        # Verify file and channel belong to this tenant
        file = await db.get(DistributionFile, file_id)
        channel = await db.get(DistributionChannel, channel_id)
        if not file or file.tenant_id != tenant_id or file.deleted_at:
            raise ValueError("文件不存在或无权访问")
        if not channel or channel.tenant_id != tenant_id or channel.deleted_at:
            raise ValueError("渠道不存在或无权访问")

        task = DistributionTask(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            file_id=file_id,
            channel_id=channel_id,
            schedule_type=schedule_type,
            schedule_config=schedule_config or {},
            scheduled_at=scheduled_at,
            status="active" if scheduled_at else "draft",
            message_text=message_text,
            created_by=created_by,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task


async def get_task(tenant_id: uuid.UUID, task_id: uuid.UUID
                   ) -> dict | None:
    async with async_session() as db:
        result = await db.execute(
            select(DistributionTask).where(
                DistributionTask.id == task_id,
                DistributionTask.tenant_id == tenant_id,
                DistributionTask.deleted_at.is_(None),
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        return _task_to_dict(task)


async def update_task(tenant_id: uuid.UUID, task_id: uuid.UUID,
                      **fields) -> DistributionTask | None:
    async with async_session() as db:
        task = await db.get(DistributionTask, task_id)
        if not task or task.tenant_id != tenant_id or task.deleted_at:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(task)
        return task


async def delete_task(tenant_id: uuid.UUID, task_id: uuid.UUID) -> bool:
    async with async_session() as db:
        task = await db.get(DistributionTask, task_id)
        if not task or task.tenant_id != tenant_id:
            return False
        task.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        return True


# ── Logs ────────────────────────────────────────────────────────────

async def get_logs(tenant_id: uuid.UUID, page: int = 1, page_size: int = 20,
                   task_id: uuid.UUID | None = None,
                   channel_id: uuid.UUID | None = None,
                   status: str | None = None
                   ) -> tuple[list[dict], int]:
    async with async_session() as db:
        base = select(DistributionLog).where(
            DistributionLog.tenant_id == tenant_id,
        )
        if task_id:
            base = base.where(DistributionLog.task_id == task_id)
        if channel_id:
            base = base.where(DistributionLog.channel_id == channel_id)
        if status:
            base = base.where(DistributionLog.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            base.order_by(DistributionLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        logs = list(result.scalars().all())
        return [_log_to_dict(l) for l in logs], total


def _log_to_dict(l: DistributionLog) -> dict:
    return {
        "id": str(l.id),
        "task_id": str(l.task_id),
        "channel_id": str(l.channel_id),
        "file_id": str(l.file_id),
        "status": str(l.status) if hasattr(l.status, "value") else l.status,
        "attempt": l.attempt,
        "request_payload": l.request_payload,
        "response_body": l.response_body,
        "error_message": l.error_message,
        "duration_ms": l.duration_ms,
        "created_at": l.created_at,
    }


# ── Execution ────────────────────────────────────────────────────────

async def execute_task(task_id: uuid.UUID) -> dict:
    """Execute a distribution task: send file to WeChat group. Returns result dict."""
    import time as _time
    from distribution.wechat_service import send_file_to_wechat_group

    async with async_session() as db:
        task = await db.get(DistributionTask, task_id)
        if not task or task.deleted_at:
            return {"error": "任务不存在"}

        channel = await db.get(DistributionChannel, task.channel_id)
        file = await db.get(DistributionFile, task.file_id)

        if not channel or not file:
            return {"error": "渠道或文件不存在"}

        webhook_url = decrypt_webhook_url(channel.webhook_url)
        file_path = get_abs_path(file.stored_path)

        if not os.path.exists(file_path):
            # Create log entry for failure
            log = DistributionLog(
                id=uuid.uuid4(),
                tenant_id=task.tenant_id,
                task_id=task.id,
                channel_id=channel.id,
                file_id=file.id,
                status="failed",
                attempt=1,
                error_message="文件在磁盘上不存在",
            )
            db.add(log)
            task.status = "failed"
            await db.commit()
            return {"error": "文件不存在"}

        # Execute
        start = _time.monotonic()
        result = await send_file_to_wechat_group(
            webhook_url, file_path, task.message_text
        )
        duration_ms = int((_time.monotonic() - start) * 1000)

        # Determine status
        log_status = "success" if not result.get("error") else "failed"

        # Create log
        log = DistributionLog(
            id=uuid.uuid4(),
            tenant_id=task.tenant_id,
            task_id=task.id,
            channel_id=channel.id,
            file_id=file.id,
            status=log_status,
            attempt=1,
            request_payload={"caption": task.message_text, "file": file.original_filename},
            response_body=result if log_status == "success" else None,
            error_message=result.get("error"),
            duration_ms=duration_ms,
        )
        db.add(log)

        # Update task status
        if task.schedule_type == "once":
            task.status = "completed" if log_status == "success" else "failed"
        else:
            task.status = "active" if log_status == "success" else "failed"
            # Compute next run time for recurring tasks
            if log_status == "success":
                from distribution.scheduler import compute_next_run
                task.scheduled_at = compute_next_run(task.schedule_type, task.schedule_config)

        await db.commit()
        return result
