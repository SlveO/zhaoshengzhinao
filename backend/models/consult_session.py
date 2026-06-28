import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class ConsultSession(Base):
    __tablename__ = "consult_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    tenant_slug: Mapped[str] = mapped_column(String(50), nullable=False, default="scnu")
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    province: Mapped[str] = mapped_column(String(50), default="")
    subject_type: Mapped[str] = mapped_column(String(20), default="")
    subjects: Mapped[str] = mapped_column(String(20), default="")
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    intent_majors: Mapped[dict] = mapped_column(JSONB, default=list)
    focus_points: Mapped[dict] = mapped_column(JSONB, default=list)
    consult_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    consult_stage: Mapped[str] = mapped_column(String(30), default="new")
    consult_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    follow_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    follow_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    followed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    followed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp(), onupdate=func.clock_timestamp())
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Session expiry: null = never expires"
    )
    context_ref_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="推荐会话绑定的最近活跃咨询会话 ID（仅推荐会话）",
    )
