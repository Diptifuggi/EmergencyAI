from __future__ import annotations

from typing import Final


_LANGUAGE_PRIMARY_TO_BCP47: Final[dict[str, str]] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "gu": "gu-IN",
    "mr": "mr-IN",
}


def primary_language(value: str | None) -> str | None:
    """Return a supported primary language without treating auto as detected."""
    if not value:
        return None
    normalized = value.strip().lower().replace("_", "-")
    if normalized in {"auto", "auto-detect", "unknown"}:
        return None
    primary = normalized.split("-", 1)[0]
    return primary if primary in _LANGUAGE_PRIMARY_TO_BCP47 else None


def bcp47_language(value: str | None) -> str | None:
    """Return the supported Indian BCP-47 code, or None when unknown/auto."""
    primary = primary_language(value)
    return _LANGUAGE_PRIMARY_TO_BCP47.get(primary) if primary else None


def sarvam_language_code(value: str | None) -> str:
    """Return Sarvam's request value: BCP-47 for fixed languages, unknown for auto."""
    return bcp47_language(value) or "unknown"
