from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class EmergencyCall(Base):
    __tablename__ = "emergency_calls"
    __table_args__ = (
        Index("ix_emergency_calls_created_at", "created_at"),
        Index("ix_emergency_calls_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    call_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text"
    )
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(35), nullable=True)
    status: Mapped[str] = mapped_column(
        String(35), nullable=False, default="received"
    )
    priority: Mapped[str] = mapped_column(
        String(35), nullable=False, default="normal"
    )
    audio_file_path: Mapped[str | None] = mapped_column(
        String(260), nullable=True
    )
    original_audio_filename: Mapped[str | None] = mapped_column(
        String(260), nullable=True
    )
    audio_content_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    audio_file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, default="flutter")
    client_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    location_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # This is derived by the server/database from the coordinates; clients do not set it.
    location_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unavailable", server_default="unavailable"
    )
    map_snapshot_file_path: Mapped[str | None] = mapped_column(String(260), nullable=True)
    map_snapshot_filename: Mapped[str | None] = mapped_column(String(260), nullable=True)
    map_snapshot_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    map_snapshot_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    map_snapshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def map_snapshot_available(self) -> bool:
        return bool(self.map_snapshot_file_path)
