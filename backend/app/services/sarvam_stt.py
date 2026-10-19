from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

from ..core.config import settings
from ..core.logger import get_logger
from ..core.language import bcp47_language, sarvam_language_code


logger = get_logger("app.services.sarvam_stt")


class SarvamTranscriptionError(Exception):
    """A safe, user-facing error from the Sarvam transcription provider."""

    def __init__(self, message: str, provider_status_code: int | None = None):
        super().__init__(message)
        self.provider_status_code = provider_status_code


async def transcribe_audio(
    *,
    audio: bytes,
    filename: str,
    content_type: str | None,
    language: str,
) -> dict[str, Any]:
    if not settings.SARVAM_API_KEY.strip():
        raise SarvamTranscriptionError("Speech transcription is not configured on the server.")
    if not audio:
        raise SarvamTranscriptionError("Uploaded audio is empty. Please record again.")

    requested_language = language.strip().lower().replace("_", "-")
    sarvam_code = sarvam_language_code(requested_language)
    data = {
        "model": settings.SARVAM_STT_MODEL,
        "language_code": sarvam_code,
        "mode": "transcribe",
    }

    logger.info(
        "[STT] Sarvam request start url=%s language_code=%s model=%s mode=%s bytes=%d content_type=%s",
        settings.SARVAM_API_URL,
        sarvam_code,
        settings.SARVAM_STT_MODEL,
        data["mode"],
        len(audio),
        content_type or "application/octet-stream",
    )
    started_at = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.SARVAM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.SARVAM_API_URL,
                headers={"api-subscription-key": settings.SARVAM_API_KEY.strip()},
                data=data,
                files={"file": (filename, audio, content_type or "application/octet-stream")},
            )
    except httpx.TimeoutException as exc:
        logger.warning(
            "[STT] Sarvam timeout error_type=%s elapsed_ms=%.1f",
            type(exc).__name__,
            (time.perf_counter() - started_at) * 1000,
        )
        raise SarvamTranscriptionError("Speech transcription timed out. Please try again.") from exc
    except httpx.HTTPError as exc:
        logger.warning(
            "[STT] Sarvam request failed error_type=%s elapsed_ms=%.1f",
            type(exc).__name__,
            (time.perf_counter() - started_at) * 1000,
        )
        raise SarvamTranscriptionError("Speech transcription service is unavailable.") from exc

    logger.info(
        "[STT] Sarvam response status=%d elapsed_ms=%.1f",
        response.status_code,
        (time.perf_counter() - started_at) * 1000,
    )
    if response.status_code in {401, 403}:
        logger.error("Sarvam STT rejected the configured API credential status=%d", response.status_code)
        raise SarvamTranscriptionError("Speech transcription is not configured correctly on the server.")
    if response.status_code >= 400:
        logger.warning("Sarvam STT returned status=%d", response.status_code)
        raise SarvamTranscriptionError(
            f"Sarvam transcription failed (HTTP {response.status_code})",
            provider_status_code=response.status_code,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SarvamTranscriptionError("Speech transcription returned an invalid response.") from exc

    transcript = str(payload.get("transcript") or payload.get("text") or "").strip()
    if not transcript:
        raise SarvamTranscriptionError("No speech was detected. Please record a clearer message.")

    returned_language = bcp47_language(str(
        payload.get("language_code")
        or payload.get("detected_language_code")
        or ""
    ).strip())
    if returned_language is None and requested_language not in {"auto", "auto-detect", "unknown"}:
        returned_language = bcp47_language(requested_language)
    return {
        "transcript": transcript,
        "language": returned_language or None,
        "requested_language": "auto" if requested_language in {"auto", "auto-detect", "unknown"} else bcp47_language(requested_language),
        "provider": "sarvam",
        "model": settings.SARVAM_STT_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    }