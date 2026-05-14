import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from . import Base


class IndustryAnalysis(Base):
    __tablename__ = "industry_analysis"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    industry_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    industry_code: Mapped[str] = mapped_column(String(20), default="")
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_annual_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_growth_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    employment_demand_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    industry_growth_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_difficulty: Mapped[str] = mapped_column(String(20), default="中等")
    popular_positions: Mapped[dict] = mapped_column(JSONB, default=dict)
    career_path: Mapped[str] = mapped_column(String(500), default="")
    pros: Mapped[dict] = mapped_column(JSONB, default=list)
    cons: Mapped[dict] = mapped_column(JSONB, default=list)
    insider_reviews: Mapped[dict] = mapped_column(JSONB, default=list)
    related_majors: Mapped[dict] = mapped_column(JSONB, default=list)
    outlook: Mapped[str] = mapped_column(String(1000), default="")
    source: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
