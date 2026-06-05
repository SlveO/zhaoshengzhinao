"""Distribution module models — channels, files, tasks, logs, access tokens."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── DistributionChannel ──────────────────────────────────────────────

class DistributionChannel(Base):
    __tablename__ = "distribution_channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    channel_type: Mapped[str] = mapped_column(
        SAEnum("wechat_group", name="distribution_channel_type"),
        nullable=False,
        default="wechat_group",
    )
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)  # encrypted at rest
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "inactive", "error", name="distribution_channel_status"),
        default="active",
    )
    last_test_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    __table_args__ = (
        Index("idx_distribution_channels_tenant", "tenant_id"),
    )


# ── DistributionFile ─────────────────────────────────────────────────

class DistributionFile(Base):
    __tablename__ = "distribution_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    __table_args__ = (
        Index("idx_distribution_files_tenant", "tenant_id"),
    )


# ── DistributionTask ─────────────────────────────────────────────────

class DistributionTask(Base):
    __tablename__ = "distribution_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_files.id"), nullable=False
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_channels.id"), nullable=False
    )
    schedule_type: Mapped[str] = mapped_column(
        SAEnum("once", "daily", "weekly", "monthly", name="distribution_schedule_type"),
        default="once",
    )
    schedule_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum("draft", "active", "paused", "completed", "failed", name="distribution_task_status"),
        default="draft",
    )
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Relationships for joined queries
    file: Mapped[DistributionFile | None] = relationship(
        "DistributionFile", foreign_keys=[file_id], lazy="joined"
    )
    channel: Mapped[DistributionChannel | None] = relationship(
        "DistributionChannel", foreign_keys=[channel_id], lazy="joined"
    )

    __table_args__ = (
        Index("idx_distribution_tasks_tenant", "tenant_id"),
        Index("idx_distribution_tasks_status_scheduled", "status", "scheduled_at"),
    )


# ── DistributionLog ──────────────────────────────────────────────────

class DistributionLog(Base):
    __tablename__ = "distribution_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_tasks.id"), nullable=False, index=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_channels.id"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_files.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        SAEnum("pending", "sending", "success", "failed", name="distribution_log_status"),
        default="pending",
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    request_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    __table_args__ = (
        Index("idx_distribution_logs_tenant", "tenant_id"),
        Index("idx_distribution_logs_task", "task_id"),
    )


# ── DistributionFileAccessToken ──────────────────────────────────────

class DistributionFileAccessToken(Base):
    __tablename__ = "distribution_file_access_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_files.id"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_channels.id"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    max_access: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    __table_args__ = (
        Index("idx_distribution_access_tokens_file", "file_id"),
    )
