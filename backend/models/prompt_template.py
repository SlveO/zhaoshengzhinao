import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base


class PromptTemplate(Base):
    """提示词模板表 — 在线编辑 + 版本控制。

    prompt_service.load_prompt 优先读取 is_active=True 的最新版本；
    若 DB 无记录则回退到 prompts_consult.py 中的代码常量。
    """
    __tablename__ = "prompt_templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_slug: Mapped[str] = mapped_column(String(50), nullable=False, default="scnu", index=True)
    prompt_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("tenant_slug", "prompt_key", "version", name="uq_prompt_version"),
    )
