from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schemas.v1 import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    ChangePasswordRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()


async def get_token_from_header(
    authorization: Optional[str] = Header(None),
) -> str:
    """Extract token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[7:]  # Remove "Bearer " prefix


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    """Register a new user."""
    
    # Check if email already exists
    existing_user = await AuthService.get_user_by_email(session, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Check if username already exists
    existing_username = await AuthService.get_user_by_username(session, payload.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    
    # Create new user
    user = await AuthService.create_user(
        session,
        username=payload.username,
        email=payload.email,
        password=payload.password,
    )
    
    # Commit the transaction
    await session.commit()
    await session.refresh(user)
    
    return AuthService.user_to_schema(user)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Login user and return JWT tokens."""
    
    # Authenticate user
    user = await AuthService.authenticate_user(session, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Create tokens
    access_token, access_expires = create_access_token({"sub": str(user.id), "type": "access"})
    refresh_token, refresh_expires = create_refresh_token({"sub": str(user.id), "type": "refresh"})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_expires,
    )


@router.get("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
async def get_current_user_endpoint(
    session: AsyncSession = Depends(get_db),
    token: str = Depends(get_token_from_header),
) -> UserOut:
    """Get current authenticated user."""
    
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
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


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db),
    token: str = Depends(get_token_from_header),
) -> dict:
    """Change password for the current user."""
    
    # Verify passwords match
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )
    
    # Get current user from token
    token_payload = decode_token(token)
    if token_payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    user_id = token_payload.get("sub")
    
    # Change password
    success = await AuthService.change_password(
        session, user_id, payload.old_password, payload.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid old password",
        )
    
    await session.commit()
    return {"message": "Password changed successfully"}


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_endpoint(
    refresh_token: str,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    user_id = payload.get("sub")
    access_token, access_expires = create_access_token({"sub": user_id, "type": "access"})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_expires,
    )

