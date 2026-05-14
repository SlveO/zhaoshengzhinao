import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    college_name: Mapped[str] = mapped_column(String(200))
    major_name: Mapped[str] = mapped_column(String(200))
    feedback_type: Mapped[str] = mapped_column(String(20))  # 'useful' | 'not_relevant'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
