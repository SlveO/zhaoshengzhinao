import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Integer, Boolean
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
    # 开发者账号标记：admin 为开发者（可见全部菜单与 DB 面板），院校账号为 False
    is_developer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
