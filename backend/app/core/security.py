from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.core.config import settings
from app.core.exceptions import InvalidTokenError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: Dict[str, Any]) -> Tuple[str, int]:
    """
    Create a JWT access token.
    
    Returns:
        tuple: (token, expires_in_seconds)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Calculate seconds until expiration
    expires_in = int((expire - datetime.now(timezone.utc)).total_seconds())
    
    return encoded_jwt, expires_in


def create_refresh_token(data: Dict[str, Any]) -> Tuple[str, int]:
    """
    Create a JWT refresh token.
    
    Returns:
        tuple: (token, expires_in_seconds)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Calculate seconds until expiration
    expires_in = int((expire - datetime.now(timezone.utc)).total_seconds())
    
    return encoded_jwt, expires_in


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    
    Returns:
        dict: Decoded token data if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        raise InvalidTokenError(str(exc))


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against its hashed version."""
    return pwd_context.verify(plain, hashed)
