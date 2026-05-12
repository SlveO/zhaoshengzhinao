import uuid
from datetime import datetime
from sqlalchemy import Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    profile_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
