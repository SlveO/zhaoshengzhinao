import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(50), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    subjects: Mapped[str] = mapped_column(String(100), default="")
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batch: Mapped[str] = mapped_column(String(20), default="本科批")
    # 注意：is_developer 已迁移至 tenant_users.role='developer'
    # users 表回归纯学生用途,不再承载管理员身份信息
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
