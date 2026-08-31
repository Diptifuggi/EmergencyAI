from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base


class SeverityScore(Base):
    __tablename__ = "severity_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    score = Column(Float, nullable=False)
    evaluated_at = Column(DateTime, nullable=False)
