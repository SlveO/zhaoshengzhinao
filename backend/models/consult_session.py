import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
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
    score: Mapped[int] = mapped_column(Integer, default=0)
    intent_majors: Mapped[dict] = mapped_column(JSONB, default=list)
    focus_points: Mapped[dict] = mapped_column(JSONB, default=list)
    consult_stage: Mapped[str] = mapped_column(String(30), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
