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


VALID_SERVICE_CATEGORIES = {
    "general",
    "police",
    "fire",
    "medical",
    "disaster",
    "women",
    "child",
    "elderly",
    "railway",
}


class SOSCreateRequest(BaseModel):
    id: UUID
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    alert_type: Literal["sos", "silent_sos", "panic_button"]
    service_category: Optional[str] = "general"
    category_source: Optional[str] = "user_selected"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_m: Optional[float] = None
    location_status: Literal["available", "last_known", "denied", "unavailable"] = "unavailable"
    triggered_at: datetime
    battery_pct: Optional[int] = Field(None, ge=0, le=100)
    network_type: Optional[str] = Field(None, max_length=50)
    device_id: Optional[str] = Field(None, max_length=128)
    app_version: Optional[str] = Field(None, max_length=50)

    @field_validator("service_category")
    @classmethod
    def validate_service_category(cls, v: Optional[str]) -> str:
        if not v:
            return "general"
        clean = v.strip().lower()
        if clean == "woman":
            clean = "women"
        if clean not in VALID_SERVICE_CATEGORIES:
            raise ValueError(
                f"Invalid service_category '{v}'. Must be one of: {sorted(VALID_SERVICE_CATEGORIES)}"
            )
        return clean


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
    service_category: str = "general"
    category_source: Optional[str] = "user_selected"
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
    service_category: str = "general"
    category_source: Optional[str] = "user_selected"
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
    service_category: str = "general"
    category_source: Optional[str] = "user_selected"
    suggested_numbers: List[str] = []
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
    emergency_contacts: List[Dict[str, Any]] = []
    location_updates: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []


class SOSStatsResponse(BaseModel):
    active_sos: int
    silent_sos: int
    panic_button: int
    pending_verification: int = 0
    trackme_active_now: int = 0
    avg_time_to_acknowledge_seconds: Optional[float] = None


class SOSMineItemOut(BaseModel):
    id: UUID
    alert_type: str
    service_category: str = "general"
    status: str
    location_status: str
    accuracy_m: Optional[float] = None
    triggered_at: datetime
    received_at: datetime
    acknowledged_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class SOSMineListResponse(BaseModel):
    items: List[SOSMineItemOut]
    total: int
    page: int
    page_size: int


class SOSMineDetailOut(BaseModel):
    id: UUID
    alert_type: str
    service_category: str = "general"
    status: str
    location_status: str
    accuracy_m: Optional[float] = None
    triggered_at: datetime
    received_at: datetime
    acknowledged_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    events: List[Dict[str, Any]] = []


class EmergencyContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str
    relation: str = Field(..., min_length=1, max_length=50)
    notify_on_sos: bool = True
    is_primary: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        norm = normalize_indian_phone(v)
        if not norm:
            raise ValueError("Phone number is required")
        return norm


class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = None
    relation: Optional[str] = Field(None, min_length=1, max_length=50)
    notify_on_sos: Optional[bool] = None
    is_primary: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_indian_phone(v)


class EmergencyContactOut(BaseModel):
    id: UUID
    name: str
    phone: str
    relation: str
    notify_on_sos: bool
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserNotificationOut(BaseModel):
    id: UUID
    alert_id: Optional[UUID] = None
    notification_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserNotificationListResponse(BaseModel):
    items: List[UserNotificationOut]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class TrackStartRequest(BaseModel):
    duration_hours: Literal[1, 2, 4, 8, 12]
    share_with_control_room: bool = False
    sos_alert_id: Optional[UUID] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    accuracy_m: Optional[float] = Field(None, ge=0.0)
    battery_pct: Optional[int] = Field(None, ge=0, le=100)


class TrackPointCreate(BaseModel):
    client_point_id: Optional[str] = Field(None, max_length=64)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy_m: Optional[float] = Field(None, ge=0.0)
    battery_pct: Optional[int] = Field(None, ge=0, le=100)
    recorded_at: Optional[datetime] = None


class TrackPointBatchCreate(BaseModel):
    points: List[TrackPointCreate] = Field(..., min_length=1, max_length=50)


class TrackAttachSOSRequest(BaseModel):
    sos_alert_id: UUID


class TrackPointOut(BaseModel):
    id: UUID
    client_point_id: Optional[str] = None
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    battery_pct: Optional[int] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class TrackSessionOut(BaseModel):
    id: UUID
    share_token: str
    duration_hours: int
    share_with_control_room: bool = False
    sos_alert_id: Optional[UUID] = None
    status: str
    started_at: datetime
    expires_at: datetime
    ended_at: Optional[datetime] = None
    distance_meters: float = 0.0
    points: List[TrackPointOut] = []

    model_config = {"from_attributes": True}


class PublicTrackPosition(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    recorded_at: datetime


class PublicTrackOut(BaseModel):
    first_name: Optional[str] = None
    status: str
    last_position: Optional[PublicTrackPosition] = None
    updated_at: Optional[datetime] = None
    expires_at: datetime


class ReverseGeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
