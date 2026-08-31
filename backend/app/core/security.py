from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import Any, Dict

from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext

from .config import settings
from .exceptions import InvalidTokenError


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(plain: str) -> str:
    """
    Hash a plain-text password.
    Bcrypt supports only 72 bytes.
    """

    if not plain:
        raise ValueError("Password cannot be empty")

    if len(plain.encode("utf-8")) > 72:
        raise ValueError(
            "Password exceeds bcrypt limit of 72 bytes"
        )

    return pwd_context.hash(plain)


def verify_password(
    plain: str,
    hashed: str
) -> bool:
    """
    Verify password against stored hash.
    """

    try:
        return pwd_context.verify(
            plain,
            hashed
        )
    except Exception:
        return False


def _create_token(
    data: Dict[str, Any],
    expires_delta: timedelta
) -> str:

    payload = data.copy()

    expire = datetime.now(UTC) + expires_delta

    payload.update({
        "exp": expire
    })

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def create_access_token(
    data: Dict[str, Any]
) -> str:

    payload = data.copy()

    payload.update({
        "type": "access"
    })

    return _create_token(
        payload,
        timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )


def create_refresh_token(
    data: Dict[str, Any]
) -> str:

    payload = data.copy()

    payload.update({
        "type": "refresh"
    })

    return _create_token(
        payload,
        timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    )


def decode_token(
    token: str
) -> Dict[str, Any]:

    try:

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

    except ExpiredSignatureError as exc:
        raise InvalidTokenError(
            "Token has expired"
        ) from exc

    except JWTError as exc:
        raise InvalidTokenError(
            "Invalid token"
        ) from exc

    token_type = payload.get("type")

    if token_type not in [
        "access",
        "refresh"
    ]:
        raise InvalidTokenError(
            "Invalid token type"
        )

    return payload