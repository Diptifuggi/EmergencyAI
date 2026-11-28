from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.dependencies import get_current_admin, get_current_citizen, get_current_user
from ...core.encryption import decrypt_field, encrypt_field
from ...core.security import hash_password, validate_password_policy
from ...models.auth_token import RefreshToken
from ...models.emergency_contact import EmergencyContact
from ...models.user import User
from ...models.user_notification import UserNotification
from ...models.user_profile import UserProfile
from ...schemas.sos import (
    EmergencyContactCreate,
    EmergencyContactOut,
    EmergencyContactUpdate,
    UnreadCountResponse,
    UserNotificationListResponse,
    UserNotificationOut,
    UserProfileOut,
    UserProfileUpdate,
)
from ...schemas.v1 import UserCreate, UserOut, UserUpdate
from ...services.auth_service import AuthService
from .audit import record_audit_log


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)

router = APIRouter()


@router.get("/me/profile", response_model=UserProfileOut)
async def get_my_profile(
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> UserProfileOut:
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        return UserProfileOut(
            user_id=current_user.id,
            email=current_user.email,
            profile_completed=False,
            blood_group="unknown",
            medical_consent=False,
        )

    return UserProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        email=current_user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        alternate_phone=profile.alternate_phone,
        guardian_phone=profile.guardian_phone,
        guardian_relation=profile.guardian_relation,
        address=profile.address,
        age=profile.age,
        blood_group=profile.blood_group or "unknown",
        allergies=decrypt_field(profile.allergies) if profile.allergies else None,
        medical_history=decrypt_field(profile.medical_history) if profile.medical_history else None,
        medical_consent=profile.medical_consent,
        medical_consent_at=profile.medical_consent_at,
        profile_completed=profile.profile_completed,
        updated_at=profile.updated_at,
    )

@router.put("/me/profile", response_model=UserProfileOut)
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> UserProfileOut:
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    profile.full_name = payload.full_name
    profile.phone = payload.phone
    profile.alternate_phone = payload.alternate_phone
    profile.guardian_phone = payload.guardian_phone
    profile.guardian_relation = payload.guardian_relation
    profile.address = payload.address
    profile.age = payload.age
    profile.blood_group = payload.blood_group or "unknown"
    profile.medical_consent = payload.medical_consent

    if payload.medical_consent:
        if payload.allergies is not None:
            profile.allergies = encrypt_field(payload.allergies)
        if payload.medical_history is not None:
            profile.medical_history = encrypt_field(payload.medical_history)
        if not profile.medical_consent_at:
            profile.medical_consent_at = datetime.now(timezone.utc)
    else:
        profile.allergies = None
        profile.medical_history = None
        profile.medical_consent_at = None

    profile.profile_completed = bool(profile.full_name and profile.phone)
    profile.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(profile)

    return UserProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        email=current_user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        alternate_phone=profile.alternate_phone,
        guardian_phone=profile.guardian_phone,
        guardian_relation=profile.guardian_relation,
        address=profile.address,
        age=profile.age,
        blood_group=profile.blood_group or "unknown",
        allergies=decrypt_field(profile.allergies) if profile.allergies else None,
        medical_history=decrypt_field(profile.medical_history) if profile.medical_history else None,
        medical_consent=profile.medical_consent,
        medical_consent_at=profile.medical_consent_at,
        profile_completed=profile.profile_completed,
        updated_at=profile.updated_at,
    )


@router.get("/me/emergency-contacts", response_model=list[EmergencyContactOut])
async def list_my_emergency_contacts(
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> list[EmergencyContactOut]:
    stmt = (
        select(EmergencyContact)
        .where(EmergencyContact.user_id == current_user.id)
        .order_by(EmergencyContact.is_primary.desc(), EmergencyContact.created_at.asc())
    )
    contacts = (await db.execute(stmt)).scalars().all()
    return [EmergencyContactOut.model_validate(c) for c in contacts]


@router.post("/me/emergency-contacts", response_model=EmergencyContactOut, status_code=status.HTTP_201_CREATED)
async def create_my_emergency_contact(
    payload: EmergencyContactCreate,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> EmergencyContactOut:
    count_stmt = select(func.count(EmergencyContact.id)).where(
        EmergencyContact.user_id == current_user.id
    )
    existing_count = (await db.execute(count_stmt)).scalar() or 0
    if existing_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 5 emergency contacts allowed.",
        )

    if payload.is_primary:
        await db.execute(
            update(EmergencyContact)
            .where(EmergencyContact.user_id == current_user.id)
            .values(is_primary=False)
        )

    contact = EmergencyContact(
        user_id=current_user.id,
        name=payload.name.strip(),
        phone=payload.phone,
        relation=payload.relation.strip(),
        notify_on_sos=payload.notify_on_sos,
        is_primary=payload.is_primary,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return EmergencyContactOut.model_validate(contact)


@router.put("/me/emergency-contacts/{contact_id}", response_model=EmergencyContactOut)
async def update_my_emergency_contact(
    contact_id: UUID,
    payload: EmergencyContactUpdate,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> EmergencyContactOut:
    contact = await db.get(EmergencyContact, contact_id)
    if not contact or contact.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Emergency contact not found")

    if payload.is_primary:
        await db.execute(
            update(EmergencyContact)
            .where(
                EmergencyContact.user_id == current_user.id,
                EmergencyContact.id != contact_id,
            )
            .values(is_primary=False)
        )

    if payload.name is not None:
        contact.name = payload.name.strip()
    if payload.phone is not None:
        contact.phone = payload.phone
    if payload.relation is not None:
        contact.relation = payload.relation.strip()
    if payload.notify_on_sos is not None:
        contact.notify_on_sos = payload.notify_on_sos
    if payload.is_primary is not None:
        contact.is_primary = payload.is_primary
    contact.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(contact)
    return EmergencyContactOut.model_validate(contact)


@router.delete("/me/emergency-contacts/{contact_id}")
async def delete_my_emergency_contact(
    contact_id: UUID,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
):
    contact = await db.get(EmergencyContact, contact_id)
    if not contact or contact.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Emergency contact not found")
    await db.delete(contact)
    await db.commit()
    return {"deleted": True, "id": str(contact_id)}


@router.get("/me/notifications", response_model=UserNotificationListResponse)
async def list_my_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> UserNotificationListResponse:
    base_query = select(UserNotification).where(UserNotification.user_id == current_user.id)
    total = (await db.execute(select(func.count()).select_from(base_query.subquery()))).scalar() or 0
    unread_count = (
        await db.execute(
            select(func.count(UserNotification.id)).where(
                UserNotification.user_id == current_user.id,
                UserNotification.is_read.is_(False),
            )
        )
    ).scalar() or 0

    rows = (
        await db.execute(
            base_query.order_by(UserNotification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return UserNotificationListResponse(
        items=[UserNotificationOut.model_validate(n) for n in rows],
        total=total,
        unread_count=unread_count,
    )


@router.get("/me/notifications/unread-count", response_model=UnreadCountResponse)
async def get_my_unread_notification_count(
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    unread_count = (
        await db.execute(
            select(func.count(UserNotification.id)).where(
                UserNotification.user_id == current_user.id,
                UserNotification.is_read.is_(False),
            )
        )
    ).scalar() or 0
    return UnreadCountResponse(unread_count=unread_count)


@router.post("/me/notifications/read-all")
async def mark_all_my_notifications_read(
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(UserNotification)
        .where(
            UserNotification.user_id == current_user.id,
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"success": True}


@router.post("/me/notifications/{notification_id}/read")
async def mark_my_notification_read(
    notification_id: UUID,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
):
    notif = await db.get(UserNotification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    return {"success": True, "id": str(notification_id)}


@router.get("/", response_model=list[UserOut])
async def list_users(
    current_user: UserOut = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [AuthService.user_to_schema(user) for user in result.scalars().all()]


@router.get("/roles")
async def list_roles(
    current_user: UserOut = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(User.role_name, func.count(User.id))
        .group_by(User.role_name)
        .order_by(User.role_name)
    )
    return [
        {
            "id": role_name,
            "name": role_name,
            "users": int(user_count),
            "permissions": None,
            "description": None,
        }
        for role_name, user_count in result.all()
        if role_name
    ]


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: UserOut = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    try:
        validate_password_policy(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if await AuthService.get_user_by_email(db, str(payload.email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    if await AuthService.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    try:
        user = await AuthService.create_user(
            db,
            username=payload.username,
            email=str(payload.email),
            password=payload.password,
            role_name=payload.role_name or "Operator",
        )
        if payload.is_active is not None:
            user.is_active = payload.is_active
        record_audit_log(
            db,
            current_user,
            "user_created",
            "user",
            str(user.id),
            {"role_name": user.role_name},
        )
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email or username already exists") from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="User service is temporarily unavailable") from exc
    return AuthService.user_to_schema(user)

@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    current_user: UserOut = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return AuthService.user_to_schema(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: UserOut = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)
    if changes.get("is_active") is False:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
    record_audit_log(db, current_user, "user_updated", "user", str(user.id), changes)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email or username already exists") from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="User service is temporarily unavailable") from exc
    return AuthService.user_to_schema(user)


@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: UUID,
    payload: AdminResetPasswordRequest,
    current_user: UserOut = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_password_policy(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    record_audit_log(db, current_user, "password_reset", "user", str(user.id))
    await db.commit()
    return {"success": True, "user_id": str(user.id)}
