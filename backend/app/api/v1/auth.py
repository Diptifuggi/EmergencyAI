from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.security import create_access_token, create_refresh_token, verify_password, hash_password
from ...schemas.v1 import RegisterRequest, UserOut
from ...services.auth_service import AuthService

router = APIRouter()

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str
    password: str

# Temporary in-memory user store for initial foundation
_fake_user = {
    "id": 1,
    "email": "admin@emergencyiq.local",
    "password_hash": hash_password("changeme"),
    "role": "admin",
    "is_active": True,
}

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await AuthService.authenticate_user(db, payload.email, payload.password)
    if user is not None:
        user_id = str(user.id)
        role = user.role_name
    elif (
        payload.email.lower() == _fake_user["email"]
        and verify_password(payload.password, _fake_user["password_hash"])
        and _fake_user.get("is_active", False)
    ):
        # Preserve the existing demo account while supporting PostgreSQL users.
        user_id = str(_fake_user["id"])
        role = _fake_user["role"]
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token({"sub": user_id, "role": role})
    refresh = create_refresh_token({"sub": user_id})
    return {"access_token": access, "refresh_token": refresh}


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user in PostgreSQL",
)
async def register(
    payload: RegisterRequest,
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
        )
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User registration is temporarily unavailable",
        ) from exc

    return AuthService.user_to_schema(user)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(token: str):
    # decode and re-issue access token
    from ...core.security import decode_token
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    # in real world fetch user and verify
    access = create_access_token({"sub": str(user_id), "role": "user"})
    refresh = create_refresh_token({"sub": str(user_id)})
    return {"access_token": access, "refresh_token": refresh}
