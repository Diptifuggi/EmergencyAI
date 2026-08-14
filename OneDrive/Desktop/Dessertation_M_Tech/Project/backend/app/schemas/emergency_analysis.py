from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmergencyType(str, Enum):
    MEDICAL = "medical"
    POLICE = "police"
    FIRE = "fire"
    ACCIDENT = "accident"
    WOMEN_SAFETY = "women_safety"
    DOMESTIC_VIOLENCE = "domestic_violence"
    CHILD_SAFETY = "child_safety"
    ROBBERY = "robbery"
    ASSAULT = "assault"
    HARASSMENT = "harassment"
    DISASTER = "disaster"
    OTHER = "other"
    UNKNOWN = "unknown"


class HelpRequired(str, Enum):
    POLICE = "police"
    AMBULANCE = "ambulance"
    FIRE_SERVICE = "fire_service"
    RESCUE = "rescue"
    MEDICAL_ASSISTANCE = "medical_assistance"
    WOMEN_SAFETY_SUPPORT = "women_safety_support"
    CHILD_PROTECTION = "child_protection"
    MULTIPLE_SERVICES = "multiple_services"
    UNKNOWN = "unknown"


class AnalysisLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Existing emergency_calls.status values (do not break).
STATUS_RECEIVED = "received"
STATUS_PENDING_TRANSCRIPTION = "pending_transcription"

# Analysis lifecycle statuses for Phase 3 integration.
STATUS_ANALYZING = "analyzing"
STATUS_ANALYZED = "analyzed"
STATUS_ANALYSIS_FAILED = "analysis_failed"


SUPPORTED_LANGUAGES = frozenset({"en", "hi", "gu", "mr"})


class EmergencyAnalysisInput(BaseModel):
    """Input derived from an emergency_calls record."""

    model_config = ConfigDict(extra="ignore")

    text_content: str | None = None
    transcription: str | None = None
    language: str | None = None
    call_type: str

    def resolved_text(self) -> str:
        return (self.text_content or self.transcription or "").strip()

    def resolved_language(self) -> str:
        return (self.language or "en").strip().lower() or "en"


class DispatchRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended_units: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("recommended_units")
    @classmethod
    def normalize_units(cls, value: list[str]) -> list[str]:
        return [unit.strip().lower() for unit in value if unit and unit.strip()]


class EmergencyAnalysis(BaseModel):
    """Validated structured analysis suitable for client_metadata['emergency_analysis']."""

    model_config = ConfigDict(extra="forbid")

    emergency_type: EmergencyType
    help_required: list[HelpRequired] = Field(default_factory=list, max_length=10)
    emergency_keywords: list[str] = Field(default_factory=list, max_length=20)
    priority_score: int = Field(ge=0, le=100)
    priority_level: AnalysisLevel
    panic_score: int = Field(ge=0, le=100)
    panic_level: AnalysisLevel
    stress_score: int = Field(ge=0, le=100)
    stress_level: AnalysisLevel
    dispatch_recommendation: DispatchRecommendation
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("emergency_keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in value:
            cleaned = item.strip().lower()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)
        return normalized


class EmergencyAnalysisResult(BaseModel):
    """Service outcome — success carries analysis; failure carries a controlled reason."""

    model_config = ConfigDict(extra="ignore")

    success: bool
    analysis: EmergencyAnalysis | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    suggested_status: str | None = None

    def to_client_metadata_patch(self, existing: dict[str, Any] | None) -> dict[str, Any]:
        """Merge analysis or failure info into existing client_metadata without overwriting unrelated keys."""
        merged: dict[str, Any] = dict(existing or {})
        if self.success and self.analysis is not None:
            merged["emergency_analysis"] = self.analysis.model_dump()
        elif self.failure_code:
            merged["emergency_analysis_error"] = {
                "code": self.failure_code,
                "message": self.failure_message,
            }
        return merged


# Raw LLM payload before enum coercion (strings from JSON).
class _RawEmergencyAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    emergency_type: str
    help_required: list[str] = Field(default_factory=list)
    emergency_keywords: list[str] = Field(default_factory=list)
    priority_score: int
    priority_level: str
    panic_score: int
    panic_level: str
    stress_score: int
    stress_level: str
    dispatch_recommendation: dict[str, Any]
    confidence: float
