"""Pydantic request/response schemas for distribution module."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Channel Schemas ──────────────────────────────────────────────────

WECHAT_WEBHOOK_PATTERN = re.compile(
    r"^https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[a-f0-9\-]+$"
)


class ChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    channel_type: str = "wechat_group"
    webhook_url: str
    config: dict = {}

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        if not WECHAT_WEBHOOK_PATTERN.match(v):
            raise ValueError(
                "Webhook URL 格式不正确，应为 https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
            )
        return v

    @field_validator("channel_type")
    @classmethod
    def validate_channel_type(cls, v: str) -> str:
        if v != "wechat_group":
            raise ValueError("当前版本仅支持 wechat_group 渠道类型")
        return v


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    webhook_url: Optional[str] = None
    config: Optional[dict] = None

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not WECHAT_WEBHOOK_PATTERN.match(v):
            raise ValueError(
                "Webhook URL 格式不正确，应为 https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
            )
        return v


class ChannelResponse(BaseModel):
    id: str
    name: str
    channel_type: str
    webhook_url_masked: str
    config: dict
    status: str
    last_test_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── File Schemas ─────────────────────────────────────────────────────

class FileUploadResponse(BaseModel):
    id: str
    original_filename: str
    file_size: int
    mime_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FileDownloadTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    download_url: str


# ── Task Schemas ─────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    file_id: UUID
    channel_id: UUID
    schedule_type: str = "once"
    schedule_config: dict = {}
    scheduled_at: Optional[datetime] = None
    message_text: Optional[str] = Field(None, max_length=4096)

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(cls, v: str) -> str:
        if v not in ("once", "daily", "weekly", "monthly"):
            raise ValueError("schedule_type 必须是 once / daily / weekly / monthly")
        return v


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    file_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    scheduled_at: Optional[datetime] = None
    message_text: Optional[str] = Field(None, max_length=4096)


class TaskResponse(BaseModel):
    id: str
    name: str
    file_id: str
    channel_id: str
    schedule_type: str
    schedule_config: dict
    scheduled_at: Optional[datetime] = None
    status: str
    message_text: Optional[str] = None
    created_at: datetime
    # Joined fields
    file_name: Optional[str] = None
    channel_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Log Schemas ──────────────────────────────────────────────────────

class LogResponse(BaseModel):
    id: str
    task_id: str
    channel_id: str
    file_id: str
    status: str
    attempt: int
    request_payload: Optional[dict] = None
    response_body: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime
    # Joined fields
    task_name: Optional[str] = None
    channel_name: Optional[str] = None
    file_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Pagination ───────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
