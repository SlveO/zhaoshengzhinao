import uuid
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class AdmissionData(Base):
    __tablename__ = "admission_data"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    major_name: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    batch: Mapped[str] = mapped_column(String(20))
    min_score: Mapped[int] = mapped_column(Integer)
    min_rank: Mapped[int] = mapped_column(Integer)
    subject_requirements: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
