from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...core.encryption import encrypt_field
from ...core.rate_limit import login_lockout, sos_rate_limiter
from ...core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    validate_password_policy,
    verify_password,
)
from ...models.auth_token import RefreshToken
from ...models.user_profile import UserProfile
from ...schemas.sos import normalize_indian_phone
from ...schemas.v1 import ChangePasswordRequest, RegisterRequest, TokenResponse, UserOut
from ...services.auth_service import AuthService

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    all_sessions: bool = False


async def _issue_token_pair(db: AsyncSession, user_id: str, role: str) -> TokenResponse:
    access = create_access_token({"sub": user_id, "role": role})
    refresh = create_refresh_token({"sub": user_id})
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(refresh),
            expires_at=expires_at,
        )
    )
    await db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    sos_rate_limiter.check_rate_limit(f"login_ip_{client_ip}", max_requests=20, window_seconds=60.0)

    email_key = f"acct_{payload.email.strip().lower()}"
    ip_key = f"ip_{client_ip}"
    login_lockout.check_locked(email_key)
    login_lockout.check_locked(ip_key)

    user = await AuthService.authenticate_user(db, payload.email.strip(), payload.password)
    if user is None:
        login_lockout.record_failure(email_key)
        login_lockout.record_failure(ip_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    login_lockout.reset_key(email_key)
    login_lockout.reset_key(ip_key)
    return await _issue_token_pair(db, str(user.id), user.role_name)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a citizen user in PostgreSQL",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    client_ip = request.client.host if request.client else "unknown"
    sos_rate_limiter.check_rate_limit(f"register_ip_{client_ip}", max_requests=10, window_seconds=60.0)

    try:
        validate_password_policy(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if await AuthService.get_user_by_email(db, str(payload.email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    if await AuthService.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")

    phone = normalize_indian_phone(payload.phone) if payload.phone else None
    alt_phone = normalize_indian_phone(payload.alternate_phone) if payload.alternate_phone else None
    g_phone = normalize_indian_phone(payload.guardian_phone) if payload.guardian_phone else None

    if phone:
        existing_phone = (
            await db.execute(select(UserProfile.id).where(UserProfile.phone == phone))
        ).scalar_one_or_none()
        if existing_phone:
            raise HTTPException(status_code=409, detail="Phone number already registered")

    has_allergies = bool(payload.allergies and payload.allergies.strip())
    has_history = bool(payload.medical_history and payload.medical_history.strip())
    if (has_allergies or has_history) and not payload.medical_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medical consent is required to save allergies or medical history",
        )

    try:
        # Public registration always assigns citizen role "User"
        user = await AuthService.create_user(
            db,
            username=payload.username,
            email=str(payload.email),
            password=payload.password,
            role_name="User",
        )
        profile = UserProfile(
            user_id=user.id,
            full_name=payload.full_name,
            phone=phone,
            alternate_phone=alt_phone,
            guardian_phone=g_phone,
            guardian_relation=payload.guardian_relation,
            address=payload.address,
            age=payload.age,
            blood_group=payload.blood_group or "unknown",
            allergies=encrypt_field(payload.allergies) if payload.medical_consent else None,
            medical_history=encrypt_field(payload.medical_history) if payload.medical_consent else None,
            medical_consent=bool(payload.medical_consent),
            medical_consent_at=datetime.now(timezone.utc) if payload.medical_consent else None,
            profile_completed=bool(payload.full_name and phone),
        )
        db.add(profile)
        await db.commit()
        await db.refresh(user)
    except HTTPException:
        raise
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email, username, or phone already exists",
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User registration is temporarily unavailable",
        ) from exc

    return AuthService.user_to_schema(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: Optional[RefreshRequest] = None,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    raw_refresh = (payload.refresh_token if payload else None) or token
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Refresh token required")

    try:
        decoded = decode_token(raw_refresh)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {exc}")

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    t_hash = hash_token(raw_refresh)
    now = datetime.now(timezone.utc)
    stored = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == t_hash))
    ).scalar_one_or_none()

    if not stored or stored.revoked_at is not None or stored.expires_at <= now:
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    user = await AuthService.get_user_by_id(db, str(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Rotate refresh token: revoke old one and issue a fresh pair
    stored.revoked_at = now
    return await _issue_token_pair(db, str(user.id), user.role_name)


@router.post("/logout")
async def logout(
    payload: Optional[LogoutRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    if payload and payload.refresh_token:
        t_hash = hash_token(payload.refresh_token)
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == t_hash, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
    return {"success": True}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: UserOut = Depends(get_current_user)) -> UserOut:
    return current_user


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    try:
        validate_password_policy(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    user = await AuthService.get_user_by_id(db, str(current_user.id))
    if not user or not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)
    now = datetime.now(timezone.utc)
    # Revoke all active sessions on password change
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await db.commit()
    return {"success": True, "message": "Password updated and all sessions revoked"}
