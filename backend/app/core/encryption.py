from __future__ import annotations

import json
import os
from typing import Any, Optional
from cryptography.fernet import Fernet, InvalidToken

from .config import settings


def get_fernet() -> Fernet:
    """
    Get the Fernet cipher instance using PROFILE_ENCRYPTION_KEY.
    Fails clearly if the encryption key is missing or invalid.
    """
    key = settings.PROFILE_ENCRYPTION_KEY or os.getenv("PROFILE_ENCRYPTION_KEY")
    if not key or not key.strip():
        raise RuntimeError(
            "PROFILE_ENCRYPTION_KEY environment variable is not configured. "
            "Please provide a 32-byte url-safe base64 Fernet key."
        )
    try:
        return Fernet(key.strip().encode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Invalid PROFILE_ENCRYPTION_KEY configuration: {exc}"
        ) from exc


def encrypt_field(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypt a text field at rest using Fernet.
    Returns None if plaintext is None.
    """
    if plaintext is None:
        return None
    if not plaintext:
        return ""
    fernet = get_fernet()
    encrypted = fernet.encrypt(plaintext.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_field(ciphertext: Optional[str]) -> Optional[str]:
    """
    Decrypt a Fernet-encrypted text field.
    Returns None if ciphertext is None.
    """
    if ciphertext is None:
        return None
    if not ciphertext:
        return ""
    fernet = get_fernet()
    try:
        decrypted = fernet.decrypt(ciphertext.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt field: invalid encryption token or mismatched key") from exc


def encrypt_json(data: Any) -> Optional[str]:
    """
    Serialize and encrypt a dictionary or list as a Fernet token.
    """
    if data is None:
        return None
    serialized = json.dumps(data, ensure_ascii=False, default=str)
    return encrypt_field(serialized)


def decrypt_json(ciphertext: Optional[str]) -> Any:
    """
    Decrypt and deserialize a Fernet-encrypted JSON payload.
    """
    if ciphertext is None:
        return None
    plaintext = decrypt_field(ciphertext)
    if not plaintext:
        return None
    return json.loads(plaintext)
