from __future__ import annotations

import enum
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class BloodGroup(str, enum.Enum):
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "unknown"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    alternate_phone = Column(String(20), nullable=True)
    guardian_phone = Column(String(20), nullable=True)
    guardian_relation = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    age = Column(Integer, nullable=True)
    blood_group = Column(String(20), nullable=True, default="unknown")

    # Sensitive medical details encrypted at rest with Fernet
    allergies = Column(Text, nullable=True)
    medical_history = Column(Text, nullable=True)

    medical_consent = Column(Boolean, default=False, nullable=False)
    medical_consent_at = Column(DateTime(timezone=True), nullable=True)
    profile_completed = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="profile")
