from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmergencyCallTextCreate(BaseModel):
    """Create a text-only emergency report. Extra fields are ignored for forward compatibility."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., min_length=1, max_length=10000)
    language: str = Field(
        ...,
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)*$",
    )
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0)
    location_timestamp: datetime | None = None
    source: str = Field(default="flutter", min_length=1, max_length=50)
    priority: str = Field(default="normal", min_length=1, max_length=35)
    client_metadata: dict[str, Any] | None = None

    @field_validator("text", "language", "source", "priority")
    @classmethod
    def strip_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class EmergencyCallUpdate(BaseModel):
    """Partial update — only provided fields are changed. Safe for future clients."""

    model_config = ConfigDict(extra="ignore")

    transcription: str | None = Field(default=None, max_length=10000)
    text_content: str | None = Field(default=None, max_length=10000)
    status: str | None = Field(default=None, min_length=1, max_length=35)
    priority: str | None = Field(default=None, min_length=1, max_length=35)
    language: str | None = Field(default=None, min_length=2, max_length=35)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0)
    location_timestamp: datetime | None = None
    client_metadata: dict[str, Any] | None = None

    @field_validator("transcription", "text_content", "status", "priority", "language")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class EmergencyCallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    user_id: UUID | None = None
    call_type: str
    text_content: str | None = None
    language: str | None = None
    status: str
    priority: str
    audio_file_path: str | None = None
    original_audio_filename: str | None = None
    audio_content_type: str | None = None
    audio_file_size: int | None = None
    audio_url: str | None = None
    transcription: str | None = None
    source: str | None = None
    client_metadata: dict[str, Any] | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    location_timestamp: datetime | None = None
    location_address: str | None = None
    created_at: datetime
    updated_at: datetime


class EmergencyCallListOut(BaseModel):
    """Paginated list envelope — stable shape when filters/fields grow later."""

    model_config = ConfigDict(extra="ignore")

    items: list[EmergencyCallOut]
    total: int
    limit: int
    offset: int
    api_version: str = "v1"
