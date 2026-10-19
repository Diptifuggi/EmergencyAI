from __future__ import annotations

import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from ...core.config import settings
from ...core.logger import get_logger
from ...services.sarvam_stt import SarvamTranscriptionError, transcribe_audio


router = APIRouter()
logger = get_logger("app.api.v1.stt")


class TranscriptionOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool = True
    transcript: str
    language: str | None = None
    requested_language: str | None = None
    provider: str
    model: str
    timestamp: str
    metadata: dict = Field(default_factory=dict)


@router.post("/transcribe", response_model=TranscriptionOut)
async def transcribe(
    file: UploadFile = File(...),
    language_code: str | None = Form(None),
    language: str | None = Form(None),
) -> dict:
    logger.info(
        "[STT] Request received content_type=%s language_code=%s",
        file.content_type or "(missing)",
        language_code or language or "auto",
    )
    extension = os.path.splitext(file.filename or "")[1].lower()
    allowed_extensions = {
        value if value.startswith(".") else f".{value}"
        for value in settings.ALLOWED_AUDIO_EXTENSIONS
    }
    if extension not in allowed_extensions:
        raise HTTPException(status_code=422, detail="Unsupported audio format")
    audio = await file.read()
    logger.info(
        "[STT] Upload received content_type=%s file_size=%d language_code=%s",
        file.content_type or "(missing)",
        len(audio),
        language_code or language or "auto",
    )
    if not audio:
        raise HTTPException(status_code=400, detail="Uploaded audio is empty. Please record again.")
    if len(audio) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Uploaded audio exceeds the maximum allowed size")
    requested_language = (language_code or language or "auto").strip().lower()
    if requested_language not in {
        "auto", "auto-detect", "unknown", "en", "hi", "gu", "mr",
        "en-in", "hi-in", "gu-in", "mr-in",
    }:
        raise HTTPException(status_code=422, detail="Unsupported transcription language")

    try:
        logger.info(
            "[STT] Normalizing incoming language=%s before Sarvam call",
            requested_language,
        )
        logger.info(
            "[STT] Calling Sarvam api_key_loaded=%s model=%s incoming_language=%s",
            bool(settings.SARVAM_API_KEY.strip()),
            settings.SARVAM_STT_MODEL,
            requested_language,
        )
        return await transcribe_audio(
            audio=audio,
            filename=file.filename or "emergency_audio",
            content_type=file.content_type,
            language=requested_language,
        )
    except SarvamTranscriptionError as exc:
        provider_status = exc.provider_status_code
        response_status = (
            provider_status
            if provider_status is not None and 400 <= provider_status < 500
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(status_code=response_status, detail=str(exc)) from exc