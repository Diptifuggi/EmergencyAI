from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

VALID_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "unknown"}

INDIAN_PHONE_REGEX = re.compile(r"^(\+91|91|0)?([6-9]\d{9})$")


def normalize_indian_phone(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    val = value.strip().replace(" ", "").replace("-", "")
    if not val:
        return None
    match = INDIAN_PHONE_REGEX.match(val)
    if not match:
        raise ValueError(
            "Invalid Indian phone number. Must be 10 digits starting with 6-9 (optional +91)."
        )
    return f"+91{match.group(2)}"


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_relation: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    blood_group: Optional[str] = "unknown"
    allergies: Optional[str] = None
    medical_history: Optional[str] = None
    medical_consent: bool = False

    @field_validator("phone", "alternate_phone", "guardian_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_indian_phone(v)

    @field_validator("blood_group")
    @classmethod
    def validate_blood_group(cls, v: Optional[str]) -> str:
        if v is None:
            return "unknown"
        clean = v.strip()
        if clean not in VALID_BLOOD_GROUPS:
            raise ValueError(f"Invalid blood group '{v}'. Must be one of: {sorted(VALID_BLOOD_GROUPS)}")
        return clean

    @model_validator(mode="after")
    def check_medical_consent(self) -> UserProfileUpdate:
        has_allergies = bool(self.allergies and self.allergies.strip())
        has_history = bool(self.medical_history and self.medical_history.strip())
        if (has_allergies or has_history) and not self.medical_consent:
            raise ValueError("Medical consent is required to save allergies or medical history")
        return self


class UserProfileOut(BaseModel):
    id: Optional[UUID] = None
    user_id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_relation: Optional[str] = None
    address: Optional[str] = None
    age: Optional[int] = None
    blood_group: str = "unknown"
    allergies: Optional[str] = None
    medical_history: Optional[str] = None
    medical_consent: bool = False
    medical_consent_at: Optional[datetime] = None
    profile_completed: bool = False
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SOSCreateRequest(BaseModel):
    id: UUID
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    alert_type: Literal["sos", "silent_sos", "panic_button"]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_m: Optional[float] = None
    location_status: Literal["available", "last_known", "denied", "unavailable"] = "unavailable"
    triggered_at: datetime
    battery_pct: Optional[int] = Field(None, ge=0, le=100)
    network_type: Optional[str] = Field(None, max_length=50)
    device_id: Optional[str] = Field(None, max_length=128)
    app_version: Optional[str] = Field(None, max_length=50)


class SOSCreateResponse(BaseModel):
    id: UUID
    status: str
    received_at: datetime


class SOSLocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    recorded_at: Optional[datetime] = None


class SOSCancelRequest(BaseModel):
    reason: Optional[str] = "User cancelled"


class SOSActionRequest(BaseModel):
    note: Optional[str] = None


class SOSStatusResponse(BaseModel):
    id: UUID
    status: str
    alert_type: str
    triggered_at: datetime
    received_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class SOSListItemOut(BaseModel):
    id: UUID
    alert_type: str
    status: str
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_m: Optional[float] = None
    location_status: str
    triggered_at: datetime
    received_at: datetime
    acknowledged_at: Optional[datetime] = None
    age_seconds: Optional[int] = None


class SOSListResponse(BaseModel):
    items: List[SOSListItemOut]
    total: int
    page: int
    page_size: int


class SOSDetailOut(BaseModel):
    id: UUID
    idempotency_key: str
    user_id: Optional[UUID] = None
    alert_type: str
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_m: Optional[float] = None
    location_status: str
    triggered_at: datetime
    received_at: datetime
    battery_pct: Optional[int] = None
    network_type: Optional[str] = None
    device_id: Optional[str] = None
    app_version: Optional[str] = None
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    close_reason: Optional[str] = None
    profile_snapshot: Optional[Dict[str, Any]] = None
    location_updates: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []


class SOSStatsResponse(BaseModel):
    active_sos: int
    silent_sos: int
    panic_button: int
    avg_time_to_acknowledge_seconds: Optional[float] = None
