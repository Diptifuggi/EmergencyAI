from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.v1 import UserCreate, UserOut, UserUpdate
from ...services.auth_service import AuthService

router = APIRouter()

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
