from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...core.encryption import decrypt_field, encrypt_field
from ...models.user import User
from ...models.user_profile import UserProfile
from ...schemas.sos import UserProfileOut, UserProfileUpdate
from ...schemas.v1 import UserCreate, UserOut, UserUpdate
from ...services.auth_service import AuthService

router = APIRouter()


@router.get("/me/profile", response_model=UserProfileOut)
async def get_my_profile(
    current_user: UserOut = Depends(get_current_user),
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
    current_user: UserOut = Depends(get_current_user),
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


@router.get("/", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[UserOut]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [AuthService.user_to_schema(user) for user in result.scalars().all()]


@router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_db)) -> list[dict]:
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
    db: AsyncSession = Depends(get_db),
) -> UserOut:
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
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
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
