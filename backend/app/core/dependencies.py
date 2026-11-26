from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.security import decode_token
from app.services.auth_service import AuthService
from app.schemas.v1 import UserOut

OPERATOR_ROLES = {"Operator", "Supervisor", "Admin", "operator", "supervisor", "admin"}


async def get_current_user(
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    """
    Get the current authenticated user from the JWT token.
    Supports either direct token argument or standard Bearer Authorization header.
    """
    raw_token = token
    if not raw_token and authorization:
        if authorization.lower().startswith("bearer "):
            raw_token = authorization[7:].strip()
        else:
            raw_token = authorization.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(raw_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Support demo fake user id "1"
    if str(user_id) == "1":
        from datetime import datetime, UTC
        from uuid import uuid4
        return UserOut(
            id=uuid4(),
            username="admin",
            email="admin@emergencyiq.local",
            role_name="Admin",
            is_active=True,
            created_at=datetime.now(UTC),
        )

    user = await AuthService.get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthService.user_to_schema(user)


async def get_current_operator(
    current_user: UserOut = Depends(get_current_user),
) -> UserOut:
    """
    Ensure the authenticated user holds an operator/supervisor/admin role.
    Plain users receive 403 Forbidden.
    """
    if current_user.role_name not in OPERATOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Operator access required",
        )
    return current_user


async def get_optional_user(
    session: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[UserOut]:
    """
    Get the current user if authenticated, otherwise return None.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization[7:].strip()
    try:
        payload = decode_token(token)
    except Exception:
        return None

    if payload is None:
        return None

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        return None

    user = await AuthService.get_user_by_id(session, user_id)
    if user is None:
        return None

    return AuthService.user_to_schema(user)
