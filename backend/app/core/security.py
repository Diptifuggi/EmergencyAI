from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timedelta, UTC
from typing import Any, Dict

from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext

from .config import settings
from .exceptions import InvalidTokenError


def validate_password_policy(password: str) -> None:
    """Enforce password policy: min 8 chars, at least 1 uppercase, 1 lowercase, 1 digit."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")


def hash_token(raw_token: str) -> str:
    """One-way SHA-256 hash for storing refresh tokens safely in DB."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


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
        "type": "refresh",
        "jti": uuid.uuid4().hex,
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