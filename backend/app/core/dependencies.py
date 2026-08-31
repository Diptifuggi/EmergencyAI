from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.security import decode_token
from app.services.auth_service import AuthService
from app.schemas.v1 import UserOut


async def get_current_user(
    token: str = Depends(lambda: None),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    """
    Get the current authenticated user from the JWT token.
    
    This dependency requires a Bearer token in the Authorization header.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
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
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await AuthService.get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthService.user_to_schema(user)


async def get_optional_user(
    session: AsyncSession = Depends(get_db),
    authorization: Optional[str] = None,
) -> Optional[UserOut]:
    """
    Get the current user if authenticated, otherwise return None.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]  # Remove "Bearer " prefix
    payload = decode_token(token)
    if payload is None:
        return None

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        return None

    user = await AuthService.get_user_by_id(session, user_id)
    if user is None:
        return None

    return AuthService.user_to_schema(user)
