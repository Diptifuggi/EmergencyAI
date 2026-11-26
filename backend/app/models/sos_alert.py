from __future__ import annotations

import enum
import uuid
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class SOSAlertType(str, enum.Enum):
    SOS = "sos"
    SILENT_SOS = "silent_sos"
    PANIC_BUTTON = "panic_button"


class SOSStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    VERIFIED = "verified"
    CANCELLED = "cancelled"
    CLOSED = "closed"
    FALSE_ALARM = "false_alarm"


class SOSLocationStatus(str, enum.Enum):
    AVAILABLE = "available"
    LAST_KNOWN = "last_known"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"


class SOSAlert(Base):
    __tablename__ = "sos_alerts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    idempotency_key = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    alert_type = Column(
        String(30),
        nullable=False,
        index=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default=SOSStatus.PENDING.value,
        server_default=SOSStatus.PENDING.value,
        index=True,
    )

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy_m = Column(Float, nullable=True)
    location_status = Column(
        String(30),
        nullable=False,
        default=SOSLocationStatus.UNAVAILABLE.value,
        server_default=SOSLocationStatus.UNAVAILABLE.value,
    )

    triggered_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    battery_pct = Column(Integer, nullable=True)
    network_type = Column(String(50), nullable=True)
    device_id = Column(String(128), nullable=True)
    app_version = Column(String(50), nullable=True)

    profile_snapshot_encrypted = Column(Text, nullable=True)

    acknowledged_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    close_reason = Column(Text, nullable=True)

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

    user = relationship("User", foreign_keys=[user_id])
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by])
    location_updates = relationship(
        "SOSLocationUpdate",
        back_populates="alert",
        cascade="all, delete-orphan",
        order_by="SOSLocationUpdate.recorded_at.desc()",
    )
    events = relationship(
        "SOSEvent",
        back_populates="alert",
        cascade="all, delete-orphan",
        order_by="SOSEvent.created_at.asc()",
    )
    profile_access_logs = relationship(
        "SOSProfileAccessLog",
        back_populates="alert",
        cascade="all, delete-orphan",
    )


class SOSLocationUpdate(Base):
    __tablename__ = "sos_location_updates"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    alert_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sos_alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_m = Column(Float, nullable=True)
    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    alert = relationship("SOSAlert", back_populates="location_updates")


class SOSEvent(Base):
    __tablename__ = "sos_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    alert_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sos_alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor_type = Column(
        String(20),
        nullable=False,
    )  # 'user', 'operator', 'system'

    actor_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )

    event_type = Column(
        String(50),
        nullable=False,
    )

    payload = Column(
        JSONB,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    alert = relationship("SOSAlert", back_populates="events")


class SOSProfileAccessLog(Base):
    __tablename__ = "sos_profile_access_log"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    alert_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sos_alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    operator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    accessed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    alert = relationship("SOSAlert", back_populates="profile_access_logs")
    operator = relationship("User", foreign_keys=[operator_id])
