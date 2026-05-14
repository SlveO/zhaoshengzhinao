import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from . import Base


class MajorIndustryMapping(Base):
    __tablename__ = "major_industry_mapping"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    major_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    primary_industries: Mapped[dict] = mapped_column(JSONB, default=list)
    secondary_industries: Mapped[dict] = mapped_column(JSONB, default=list)
    typical_positions: Mapped[dict] = mapped_column(JSONB, default=list)
    salary_range: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
