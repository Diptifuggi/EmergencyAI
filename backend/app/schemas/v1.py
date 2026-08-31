from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID


# ==================== Authentication Schemas ====================

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


# ==================== User Schemas ====================

class UserOut(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    role_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role_name: Optional[str] = 'Operator'
    is_active: Optional[bool] = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role_name: Optional[str] = None
    is_active: Optional[bool] = None


# ==================== Call Schemas ====================

class CallOut(BaseModel):
    id: Optional[str]
    started_at: Optional[datetime]
    duration_seconds: Optional[int]


class IncidentOut(BaseModel):
    id: Optional[str]
    title: str
    created_at: Optional[datetime]


class UploadOut(BaseModel):
    filename: str
    content_type: Optional[str]


__all__ = [
    "Token",
    "TokenResponse",
    "LoginRequest",
    "RegisterRequest",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "UserOut",
    "UserCreate",
    "UserUpdate",
    "CallOut",
    "IncidentOut",
    "UploadOut",
]
