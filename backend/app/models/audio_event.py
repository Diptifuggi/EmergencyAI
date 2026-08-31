from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base


class AudioEvent(Base):
    __tablename__ = "audio_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    detected_at = Column(DateTime, nullable=False)
