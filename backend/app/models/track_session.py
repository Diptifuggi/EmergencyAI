from __future__ import annotations

import enum
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TrackSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    EXPIRED = "expired"


class TrackSession(Base):
    __tablename__ = "track_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    share_token = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    duration_hours = Column(Integer, nullable=False)
    share_with_control_room = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    sos_alert_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sos_alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(
        String(30),
        nullable=False,
        default=TrackSessionStatus.ACTIVE.value,
        server_default=TrackSessionStatus.ACTIVE.value,
        index=True,
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", foreign_keys=[user_id])
    points = relationship(
        "TrackPoint",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class TrackPoint(Base):
    __tablename__ = "track_points"
    __table_args__ = (
        UniqueConstraint("session_id", "client_point_id", name="uq_track_point_client_id"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("track_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_point_id = Column(String(64), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_m = Column(Float, nullable=True)
    battery_pct = Column(Integer, nullable=True)

    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    session = relationship("TrackSession", back_populates="points")
