import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class College(Base):
    __tablename__ = "colleges"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    type: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(50))
    province: Mapped[str] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(50))
    is_985: Mapped[bool] = mapped_column(Boolean, default=False)
    is_211: Mapped[bool] = mapped_column(Boolean, default=False)
    is_double_first: Mapped[bool] = mapped_column(Boolean, default=False)
    intro: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
