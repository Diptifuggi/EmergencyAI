from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TranscriptCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    transcript_text: str = Field(min_length=1, max_length=10000)
    language: str = Field(
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)*$",
    )
    source: str = Field(default="flutter_stt", min_length=1, max_length=50)

    @field_validator("transcript_text", "language", "source")
    @classmethod
    def strip_required_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    user_id: UUID | None = None
    transcript_text: str
    language: str
    source: str
    created_at: datetime
