from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import BASE_DIR, settings
from ...core.database import async_session, get_db
from ...core.dependencies import get_current_citizen, get_current_operator, get_optional_user
from ...core.exceptions import FileTooLargeError, InvalidFileTypeError
from ...core.language import bcp47_language
from ...core.logger import get_logger
from ...core.ws_manager import ws_manager
from ...models.emergency_call import EmergencyCall
from ...schemas.emergency_call import (
    EmergencyCallListOut,
    EmergencyCallManualCreate,
    EmergencyCallOut,
    EmergencyCallTextCreate,
    EmergencyCallUpdate,
)
from ...schemas.v1 import UserOut
from .audit import record_audit_log
from ...services.emergency_call_analysis_runner import (
    has_analyzable_transcript,
    run_post_create_analysis_in_background,
)
from ...services.location_service import reverse_geocode
from ...services.map_snapshot_storage import MAP_SNAPSHOT_DIR, resolve_map_snapshot_path


router = APIRouter()
logger = get_logger("app.api.v1.emergency_calls")

SUPPORTED_EMERGENCY_LANGUAGES = {"auto", "en", "hi", "gu", "mr"}


def _validate_language(language: str) -> str:
    normalized = language.strip().lower().replace("_", "-")
    if normalized in {"en-in", "hi-in", "gu-in", "mr-in"}:
        return normalized
    if normalized not in SUPPORTED_EMERGENCY_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="language must be auto, en, hi, gu, or mr",
        )
    return normalized if normalized == "auto" else bcp47_language(normalized) or normalized


def _persisted_language(language: str) -> str | None:
    """Persist detected BCP-47 language; auto remains only request metadata."""
    return None if language == "auto" else bcp47_language(language) or language

UPLOAD_DIR = BASE_DIR / "backend" / "storage" / "audio"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAP_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _location_address_state(
    latitude: float | None,
    longitude: float | None,
    reported_address: str | None,
) -> tuple[str | None, str]:
    if reported_address and reported_address.strip():
        return reported_address.strip(), "reported"
    if latitude is not None and longitude is not None:
        return None, "pending"
    return None, "unavailable"


async def _resolve_location_address_background(
    call_id: uuid.UUID,
    latitude: float,
    longitude: float,
) -> None:
    address = await reverse_geocode(latitude, longitude)
    async with async_session() as db:
        result = await db.execute(
            select(EmergencyCall)
            .where(EmergencyCall.id == call_id)
            .with_for_update()
        )
        emergency = result.scalar_one_or_none()
        if (
            emergency is None
            or emergency.latitude != latitude
            or emergency.longitude != longitude
            or emergency.location_address_status != "pending"
            or emergency.location_address
        ):
            return
        emergency.location_address = address
        emergency.location_address_status = "resolved" if address else "failed"
        await db.commit()


def _schedule_location_address(
    background_tasks: BackgroundTasks,
    emergency: EmergencyCall,
) -> None:
    if (
        emergency.location_address_status == "pending"
        and emergency.latitude is not None
        and emergency.longitude is not None
    ):
        background_tasks.add_task(
            _resolve_location_address_background,
            emergency.id,
            emergency.latitude,
            emergency.longitude,
        )


def _parse_location_timestamp(raw: str | None) -> datetime | None:
    if raw is None or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="location_timestamp must be a valid ISO-8601 timestamp",
        ) from exc


def _validate_coordinates(latitude: float | None, longitude: float | None, accuracy: float | None) -> None:
    if latitude is not None and (latitude < -90 or latitude > 90):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="latitude must be between -90 and 90",
        )
    if longitude is not None and (longitude < -180 or longitude > 180):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="longitude must be between -180 and 180",
        )
    if accuracy is not None and accuracy < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="location_accuracy must be non-negative",
        )


def _location_status(latitude: float | None, longitude: float | None) -> str:
    """Return the persisted location state from a complete GPS coordinate pair."""
    return "captured" if latitude is not None and longitude is not None else "unavailable"


def _validated_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip()
    if not key or not key.isascii() or len(key) > 128 or not all(
        character.isalnum() or character in "-._~" for character in key
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must contain 1-128 safe characters",
        )
    return key


async def _find_idempotent_emergency(
    db: AsyncSession,
    idempotency_key: str | None,
) -> EmergencyCall | None:
    if idempotency_key is None:
        return None
    return await db.scalar(
        select(EmergencyCall).where(EmergencyCall.idempotency_key == idempotency_key)
    )


def _schedule_emergency_analysis(
    background_tasks: BackgroundTasks,
    emergency: EmergencyCall,
) -> None:
    if has_analyzable_transcript(emergency):
        background_tasks.add_task(
            run_post_create_analysis_in_background,
            emergency.id,
        )


def _parse_metadata(raw: str | None) -> dict[str, Any] | None:
    if raw is None or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="client_metadata must be valid JSON",
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="client_metadata must be a JSON object",
        )
    return parsed


def _merge_client_metadata(
    existing: dict[str, Any] | None,
    patch: dict[str, Any],
) -> dict[str, Any]:
    return {
        **(existing or {}),
        **{key: value for key, value in patch.items() if value is not None},
    }


def _looks_like_mp3(contents: bytes) -> bool:
    """Accept ID3-tagged files or MPEG audio frame headers, not placeholder text."""
    if contents.startswith(b"ID3"):
        return True
    return len(contents) >= 2 and contents[0] == 0xFF and (contents[1] & 0xE0) == 0xE0


def _resolve_ffmpeg_path() -> str | None:
    ffmpeg_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if ffmpeg_path:
        return ffmpeg_path

    try:
        import imageio_ffmpeg

        candidate = imageio_ffmpeg.get_ffmpeg_exe()
        if candidate and os.path.exists(candidate):
            return candidate
    except Exception:
        pass

    return None


def convert_uploaded_audio_to_mp3(audio_bytes: bytes, original_filename: str) -> tuple[bytes, str, str]:
    """Normalize uploaded voice files to MP3 for reliable storage and playback."""
    ext = os.path.splitext(original_filename)[1].lower()
    if ext == ".mp3":
        return audio_bytes, ".mp3", "audio/mpeg"

    ffmpeg_path = _resolve_ffmpeg_path()
    if ffmpeg_path is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audio conversion requires FFmpeg to be installed on the server.",
        )

    # Create temporary files and close them immediately to release the file handle lock on Windows.
    source_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    
    source_path = Path(source_file.name)
    output_path = Path(output_file.name)

    try:
        source_file.write(audio_bytes)
        source_file.close()
        output_file.close()

        completed = subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            logger.warning(
                "Audio conversion failed error_type=ffmpeg_nonzero_exit inputBytes=%d",
                len(audio_bytes),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio is not a valid or supported recording",
            )

        converted_bytes = output_path.read_bytes()
        if not converted_bytes:
            logger.warning("Audio conversion produced empty output inputBytes=%d", len(audio_bytes))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio conversion produced no audio data",
            )
        return converted_bytes, ".mp3", "audio/mpeg"
    finally:
        if source_path.exists():
            source_path.unlink(missing_ok=True)
        if output_path.exists():
            output_path.unlink(missing_ok=True)


async def _save_audio_file(file: UploadFile) -> tuple[str, str, str, int]:
    filename = file.filename or "audio.bin"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise InvalidFileTypeError(f"Extension {ext} not allowed")

    contents = await file.read()
    logger.info(
        "Audio upload received contentType=%s bytes=%d field=file",
        file.content_type or "unknown",
        len(contents),
    )
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio is empty. Please record again.",
        )
    if ext == ".mp3" and not _looks_like_mp3(contents):
        logger.warning("Audio upload rejected invalid MP3 bytes=%d", len(contents))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded MP3 does not contain a valid audio header",
        )
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise FileTooLargeError("Uploaded audio exceeds maximum allowed size")

    converted_bytes, converted_ext, content_type = convert_uploaded_audio_to_mp3(contents, filename)
    if not converted_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio is empty after conversion")
    if converted_ext == ".mp3" and not _looks_like_mp3(converted_bytes):
        logger.warning("Audio conversion produced invalid MP3 bytes=%d", len(converted_bytes))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio could not be converted to a valid MP3",
        )
    unique_filename = f"{uuid.uuid4().hex}{converted_ext}"
    target_path = UPLOAD_DIR / unique_filename
    try:
        target_path.write_bytes(converted_bytes)
    except OSError as exc:
        logger.exception("Failed to save uploaded audio file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save uploaded audio",
        ) from exc

    relative_path = str(Path("backend") / "storage" / "audio" / unique_filename)
    final_size = target_path.stat().st_size
    logger.info(
        "Audio upload stored receivedBytes=%d writtenBytes=%d",
        len(contents),
        len(converted_bytes),
    )
    if final_size != len(converted_bytes):
        raise HTTPException(status_code=500, detail="Stored audio size verification failed")
    return relative_path, filename, content_type, final_size


async def _save_map_snapshot(file: UploadFile) -> tuple[str, str, str, int]:
    filename = file.filename or "map_snapshot.png"
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise InvalidFileTypeError("Map snapshot must be PNG, JPEG, or WebP")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="Map snapshot must not be empty")
    if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise FileTooLargeError("Map snapshot exceeds maximum allowed size")
    extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[content_type]
    unique_filename = f"{uuid.uuid4().hex}{extension}"
    target_path = MAP_SNAPSHOT_DIR / unique_filename
    try:
        target_path.write_bytes(contents)
    except OSError as exc:
        logger.exception("Failed to save map snapshot: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to save map snapshot") from exc
    return str(Path("backend") / "storage" / "map_snapshots" / unique_filename), filename, content_type, len(contents)


@router.post("/text", response_model=EmergencyCallOut, status_code=status.HTTP_201_CREATED)
async def create_text_emergency(
    payload: EmergencyCallTextCreate,
    background_tasks: BackgroundTasks,
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: UserOut | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    started_at = time.perf_counter()
    idempotency_key = _validated_idempotency_key(idempotency_header)
    existing = await _find_idempotent_emergency(db, idempotency_key)
    if existing is not None:
        logger.info("Idempotent emergency retry reused emergency_id=%s", existing.id)
        return existing

    requested_language = _validate_language(payload.language)
    metadata = dict(payload.client_metadata or {})
    metadata.setdefault("requested_language", requested_language)
    location_address, address_status = _location_address_state(
        payload.latitude,
        payload.longitude,
        payload.location_address,
    )
    emergency = EmergencyCall(
        user_id=current_user.id if current_user else None,
        call_type="text",
        text_content=payload.text,
        language=_persisted_language(requested_language),
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_accuracy=payload.location_accuracy,
        location_timestamp=payload.location_timestamp,
        location_address=location_address,
        location_address_status=address_status,
        location_status=_location_status(payload.latitude, payload.longitude),
        source=payload.source,
        priority=payload.priority,
        idempotency_key=idempotency_key,
        client_metadata=metadata,
        status="analyzing" if payload.text.strip() else "received",
    )

    try:
        db.add(emergency)
        database_started_at = time.perf_counter()
        await db.commit()
        await db.refresh(emergency)
        logger.info(
            "Emergency database persistence complete emergency_id=%s elapsed_ms=%.1f",
            emergency.id,
            (time.perf_counter() - database_started_at) * 1000,
        )
    except IntegrityError as exc:
        await db.rollback()
        existing = await _find_idempotent_emergency(db, idempotency_key)
        if existing is not None:
            logger.info("Concurrent idempotent retry reused emergency_id=%s", existing.id)
            return existing
        logger.error("Failed to persist text emergency error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to persist text emergency error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc

    _schedule_emergency_analysis(background_tasks, emergency)
    _schedule_location_address(background_tasks, emergency)
    await ws_manager.broadcast(
        "operator",
        {"event": "report.created", "call_id": str(emergency.id), "call_type": emergency.call_type},
    )
    logger.info(
        "Emergency request persisted emergency_id=%s elapsed_ms=%.1f analysis_scheduled=%s",
        emergency.id,
        (time.perf_counter() - started_at) * 1000,
        has_analyzable_transcript(emergency),
    )
    return emergency


@router.post("/manual", response_model=EmergencyCallOut, status_code=status.HTTP_201_CREATED)
async def create_manual_emergency(
    payload: EmergencyCallManualCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    """Persist caller/operator metadata without fabricating emergency text."""
    _validate_coordinates(payload.latitude, payload.longitude, None)
    metadata = {
        "caller_name": payload.caller_name,
        "caller_phone": payload.caller_phone,
        "call_started_at": payload.started_at.isoformat() if payload.started_at else None,
        "platform": "react_operator",
    }
    location_address, address_status = _location_address_state(
        payload.latitude,
        payload.longitude,
        payload.location_address,
    )
    emergency = EmergencyCall(
        call_type="manual",
        status="received",
        priority="normal",
        source=payload.source,
        client_metadata=metadata,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_address=location_address,
        location_address_status=address_status,
        location_status=_location_status(payload.latitude, payload.longitude),
    )
    try:
        db.add(emergency)
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to persist manual emergency: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc
    _schedule_location_address(background_tasks, emergency)
    return emergency


@router.post("/audio", response_model=EmergencyCallOut, status_code=status.HTTP_201_CREATED)
async def create_audio_emergency(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(...),
    transcription: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    location_accuracy: float | None = Form(None),
    location_timestamp: str | None = Form(None),
    location_address: str | None = Form(None),
    source: str = Form("flutter"),
    priority: str = Form("normal"),
    existing_call_id: uuid.UUID | None = Form(None),
    client_metadata: str | None = Form(None),
    map_snapshot: UploadFile | None = File(None),
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: UserOut | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    """
    Store voice audio and optional matching text (STT / typed transcript).

    Multipart fields:
    - file: audio (required)
    - language: e.g. en, hi, gu (required)
    - transcription: text of the voice (optional; recommended from Flutter STT)
    - latitude / longitude / source / priority / client_metadata (optional JSON string)
    """
    started_at = time.perf_counter()
    idempotency_key = _validated_idempotency_key(idempotency_header)
    existing_by_key = await _find_idempotent_emergency(db, idempotency_key)
    if existing_by_key is not None:
        logger.info("Idempotent emergency retry reused emergency_id=%s", existing_by_key.id)
        return existing_by_key

    _validate_coordinates(latitude, longitude, location_accuracy)
    requested_language = _validate_language(language)
    cleaned_language = _persisted_language(requested_language)
    existing_emergency = await db.get(EmergencyCall, existing_call_id) if existing_call_id else None
    if existing_call_id and existing_emergency is None:
        raise HTTPException(status_code=404, detail="Emergency call not found")
    relative_path, original_name, content_type, size_bytes = await _save_audio_file(file)
    snapshot_data = await _save_map_snapshot(map_snapshot) if map_snapshot else None
    meta = _parse_metadata(client_metadata) or {}
    meta.setdefault("requested_language", requested_language)
    cleaned_transcription = (transcription or "").strip() or None

    if existing_call_id is not None:
        result = await db.execute(
            select(EmergencyCall)
            .where(EmergencyCall.id == existing_call_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        existing_emergency = result.scalar_one_or_none()
        if existing_emergency is None:
            raise HTTPException(status_code=404, detail="Emergency call not found")

    if existing_emergency is not None:
        existing_emergency.client_metadata = _merge_client_metadata(
            existing_emergency.client_metadata,
            meta,
        )
        if idempotency_key is not None:
            existing_emergency.idempotency_key = idempotency_key
        existing_emergency.audio_file_path = relative_path
        existing_emergency.original_audio_filename = original_name
        existing_emergency.audio_content_type = content_type
        existing_emergency.audio_file_size = size_bytes
        existing_emergency.audio_url = str(
            request.url_for("get_emergency_audio_file", call_id=existing_emergency.id)
        )
        existing_emergency.language = cleaned_language or existing_emergency.language
        existing_emergency.transcription = cleaned_transcription
        existing_emergency.text_content = cleaned_transcription or existing_emergency.text_content
        existing_emergency.status = "received" if cleaned_transcription else "pending_transcription"
        if cleaned_transcription:
            existing_emergency.status = "analyzing"
        previous_coordinates = (existing_emergency.latitude, existing_emergency.longitude)
        if latitude is not None:
            existing_emergency.latitude = latitude
        if longitude is not None:
            existing_emergency.longitude = longitude
        if location_accuracy is not None:
            existing_emergency.location_accuracy = location_accuracy
        if location_timestamp is not None:
            existing_emergency.location_timestamp = _parse_location_timestamp(location_timestamp)
        if location_address and location_address.strip():
            existing_emergency.location_address = location_address.strip()
            existing_emergency.location_address_status = "reported"
        elif (existing_emergency.latitude, existing_emergency.longitude) != previous_coordinates:
            if existing_emergency.location_address_status == "resolved":
                existing_emergency.location_address = None
            existing_emergency.location_address_status = (
                "pending"
                if existing_emergency.latitude is not None
                and existing_emergency.longitude is not None
                else "unavailable"
            )
        existing_emergency.location_status = _location_status(
            existing_emergency.latitude,
            existing_emergency.longitude,
        )
        if snapshot_data:
            existing_emergency.map_snapshot_file_path = snapshot_data[0]
            existing_emergency.map_snapshot_filename = snapshot_data[1]
            existing_emergency.map_snapshot_content_type = snapshot_data[2]
            existing_emergency.map_snapshot_size = snapshot_data[3]
            existing_emergency.map_snapshot_url = str(
                request.url_for("get_emergency_map_snapshot", call_id=existing_emergency.id)
            )
        try:
            database_started_at = time.perf_counter()
            await db.commit()
            await db.refresh(existing_emergency)
            logger.info(
                "Emergency database persistence complete emergency_id=%s elapsed_ms=%.1f",
                existing_emergency.id,
                (time.perf_counter() - database_started_at) * 1000,
            )
        except IntegrityError as exc:
            await db.rollback()
            duplicate = await _find_idempotent_emergency(db, idempotency_key)
            if duplicate is not None:
                logger.info("Concurrent idempotent retry reused emergency_id=%s", duplicate.id)
                return duplicate
            logger.error("Failed to attach audio to emergency error_type=%s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Emergency storage is temporarily unavailable",
            ) from exc
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.error("Failed to attach audio to emergency error_type=%s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Emergency storage is temporarily unavailable",
            ) from exc
        _schedule_emergency_analysis(background_tasks, existing_emergency)
        _schedule_location_address(background_tasks, existing_emergency)
        logger.info(
            "Emergency request persisted emergency_id=%s elapsed_ms=%.1f analysis_scheduled=%s",
            existing_emergency.id,
            (time.perf_counter() - started_at) * 1000,
            has_analyzable_transcript(existing_emergency),
        )
        return existing_emergency

    status_value = "received" if cleaned_transcription else "pending_transcription"
    address, address_status = _location_address_state(
        latitude,
        longitude,
        location_address,
    )
    emergency = EmergencyCall(
        call_type="audio",
        language=cleaned_language,
        status=status_value,
        priority=(priority or "normal").strip() or "normal",
        audio_file_path=relative_path,
        original_audio_filename=original_name,
        audio_content_type=content_type,
        audio_file_size=size_bytes,
        user_id=current_user.id if current_user else None,
        transcription=cleaned_transcription,
        text_content=cleaned_transcription,
        source=(source or "flutter").strip() or "flutter",
        idempotency_key=idempotency_key,
        client_metadata=meta,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=location_accuracy,
        location_timestamp=_parse_location_timestamp(location_timestamp),
        location_address=address,
        location_address_status=address_status,
        location_status=_location_status(latitude, longitude),
        map_snapshot_file_path=snapshot_data[0] if snapshot_data else None,
        map_snapshot_filename=snapshot_data[1] if snapshot_data else None,
        map_snapshot_content_type=snapshot_data[2] if snapshot_data else None,
        map_snapshot_size=snapshot_data[3] if snapshot_data else None,
    )

    try:
        db.add(emergency)
        await db.flush()
        emergency.audio_url = str(
            request.url_for("get_emergency_audio_file", call_id=emergency.id)
        )
        if snapshot_data:
            emergency.map_snapshot_url = str(
                request.url_for("get_emergency_map_snapshot", call_id=emergency.id)
            )
        if cleaned_transcription:
            emergency.status = "analyzing"
        database_started_at = time.perf_counter()
        await db.commit()
        await db.refresh(emergency)
        logger.info(
            "Emergency database persistence complete emergency_id=%s elapsed_ms=%.1f",
            emergency.id,
            (time.perf_counter() - database_started_at) * 1000,
        )
    except IntegrityError as exc:
        await db.rollback()
        duplicate = await _find_idempotent_emergency(db, idempotency_key)
        if duplicate is not None:
            logger.info("Concurrent idempotent retry reused emergency_id=%s", duplicate.id)
            return duplicate
        logger.error("Failed to persist audio emergency metadata error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to persist audio emergency metadata error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc

    _schedule_emergency_analysis(background_tasks, emergency)
    _schedule_location_address(background_tasks, emergency)
    await ws_manager.broadcast(
        "operator",
        {"event": "report.created", "call_id": str(emergency.id), "call_type": emergency.call_type},
    )
    logger.info(
        "Emergency request persisted emergency_id=%s elapsed_ms=%.1f analysis_scheduled=%s",
        emergency.id,
        (time.perf_counter() - started_at) * 1000,
        has_analyzable_transcript(emergency),
    )
    return emergency


@router.post(
    "/voice-text",
    response_model=EmergencyCallOut,
    status_code=status.HTTP_201_CREATED,
    summary="Store voice + text together (Flutter primary endpoint)",
)
async def create_voice_and_text_emergency(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    transcription: str = Form(...),
    language: str = Form(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    location_accuracy: float | None = Form(None),
    location_timestamp: str | None = Form(None),
    location_address: str | None = Form(None),
    source: str = Form("flutter"),
    priority: str = Form("normal"),
    client_metadata: str | None = Form(None),
    map_snapshot: UploadFile | None = File(None),
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: UserOut | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    """Requires both audio file and its text. Prefer this from the Flutter app."""
    started_at = time.perf_counter()
    idempotency_key = _validated_idempotency_key(idempotency_header)
    existing = await _find_idempotent_emergency(db, idempotency_key)
    if existing is not None:
        logger.info("Idempotent emergency retry reused emergency_id=%s", existing.id)
        return existing

    _validate_coordinates(latitude, longitude, location_accuracy)
    requested_language = _validate_language(language)
    cleaned_language = _persisted_language(requested_language)
    cleaned = transcription.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="transcription must not be empty",
        )

    relative_path, original_name, content_type, size_bytes = await _save_audio_file(file)
    snapshot_data = await _save_map_snapshot(map_snapshot) if map_snapshot else None
    meta = _parse_metadata(client_metadata) or {}
    meta.setdefault("requested_language", requested_language)
    address, address_status = _location_address_state(
        latitude,
        longitude,
        location_address,
    )

    emergency = EmergencyCall(
        user_id=current_user.id if current_user else None,
        call_type="voice_text",
        language=cleaned_language,
        status="analyzing",
        priority=(priority or "normal").strip() or "normal",
        audio_file_path=relative_path,
        original_audio_filename=original_name,
        audio_content_type=content_type,
        audio_file_size=size_bytes,
        idempotency_key=idempotency_key,
        transcription=cleaned,
        text_content=cleaned,
        source=(source or "flutter").strip() or "flutter",
        client_metadata=meta,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=location_accuracy,
        location_timestamp=_parse_location_timestamp(location_timestamp),
        location_address=address,
        location_address_status=address_status,
        location_status=_location_status(latitude, longitude),
        map_snapshot_file_path=snapshot_data[0] if snapshot_data else None,
        map_snapshot_filename=snapshot_data[1] if snapshot_data else None,
        map_snapshot_content_type=snapshot_data[2] if snapshot_data else None,
        map_snapshot_size=snapshot_data[3] if snapshot_data else None,
    )

    try:
        db.add(emergency)
        await db.flush()
        emergency.audio_url = str(
            request.url_for("get_emergency_audio_file", call_id=emergency.id)
        )
        if snapshot_data:
            emergency.map_snapshot_url = str(
                request.url_for("get_emergency_map_snapshot", call_id=emergency.id)
            )
        database_started_at = time.perf_counter()
        await db.commit()
        await db.refresh(emergency)
        logger.info(
            "Emergency database persistence complete emergency_id=%s elapsed_ms=%.1f",
            emergency.id,
            (time.perf_counter() - database_started_at) * 1000,
        )
    except IntegrityError as exc:
        await db.rollback()
        existing = await _find_idempotent_emergency(db, idempotency_key)
        if existing is not None:
            logger.info("Concurrent idempotent retry reused emergency_id=%s", existing.id)
            return existing
        logger.error("Failed to persist voice+text emergency error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Failed to persist voice+text emergency error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc

    _schedule_emergency_analysis(background_tasks, emergency)
    _schedule_location_address(background_tasks, emergency)
    await ws_manager.broadcast(
        "operator",
        {"event": "report.created", "call_id": str(emergency.id), "call_type": emergency.call_type},
    )
    logger.info(
        "Emergency request persisted emergency_id=%s elapsed_ms=%.1f analysis_scheduled=%s",
        emergency.id,
        (time.perf_counter() - started_at) * 1000,
        has_analyzable_transcript(emergency),
    )
    return emergency


@router.get("/mine", response_model=EmergencyCallListOut)
async def list_my_emergency_calls(
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> EmergencyCallListOut:
    count_stmt = select(func.count()).select_from(EmergencyCall).where(EmergencyCall.user_id == current_user.id)
    list_stmt = (
        select(EmergencyCall)
        .where(EmergencyCall.user_id == current_user.id)
        .order_by(EmergencyCall.created_at.desc())
    )
    total = int((await db.execute(count_stmt)).scalar_one())
    result = await db.execute(list_stmt.offset(offset).limit(limit))
    items = list(result.scalars().all())
    return EmergencyCallListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/", response_model=EmergencyCallListOut)
async def list_emergency_calls(
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    call_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
) -> EmergencyCallListOut:
    filters = []
    if call_type:
        filters.append(EmergencyCall.call_type == call_type.strip())
    if status_filter:
        filters.append(EmergencyCall.status == status_filter.strip())

    count_stmt = select(func.count()).select_from(EmergencyCall)
    list_stmt = select(EmergencyCall).order_by(EmergencyCall.created_at.desc())
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)

    total = int((await db.execute(count_stmt)).scalar_one())
    result = await db.execute(list_stmt.offset(offset).limit(limit))
    items = list(result.scalars().all())
    return EmergencyCallListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/{call_id}", response_model=EmergencyCallOut)
async def get_emergency_call(
    call_id: uuid.UUID,
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    result = await db.get(EmergencyCall, call_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency call not found")
    return result


@router.patch("/{call_id}", response_model=EmergencyCallOut)
async def update_emergency_call(
    call_id: uuid.UUID,
    payload: EmergencyCallUpdate,
    background_tasks: BackgroundTasks,
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    """Update transcription/status/metadata later without breaking clients."""
    result = await db.execute(
        select(EmergencyCall)
        .where(EmergencyCall.id == call_id)
        .with_for_update()
    )
    emergency = result.scalar_one_or_none()
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency call not found")

    updates = payload.model_dump(exclude_unset=True)
    for field in (
        "latitude",
        "longitude",
        "location_accuracy",
        "location_timestamp",
        "client_metadata",
        "location_address",
    ):
        if field in updates and updates[field] is None:
            updates.pop(field)

    latitude = updates.get("latitude", emergency.latitude)
    longitude = updates.get("longitude", emergency.longitude)
    coordinates_updated = "latitude" in updates or "longitude" in updates
    if coordinates_updated:
        _validate_coordinates(
            latitude,
            longitude,
            updates.get("location_accuracy", emergency.location_accuracy),
        )
        if (latitude is None) != (longitude is None):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="latitude and longitude must be provided together",
            )

    if "client_metadata" in updates:
        updates["client_metadata"] = _merge_client_metadata(
            emergency.client_metadata,
            updates["client_metadata"],
        )

    previous_coordinates = (emergency.latitude, emergency.longitude)
    for key, value in updates.items():
        setattr(emergency, key, value)

    coordinates_changed = (emergency.latitude, emergency.longitude) != previous_coordinates
    if "location_address" in updates:
        emergency.location_address_status = "reported"
    if "latitude" in updates or "longitude" in updates:
        emergency.location_status = _location_status(emergency.latitude, emergency.longitude)
    if coordinates_changed and "location_address" not in updates:
        if emergency.location_address_status == "resolved":
            emergency.location_address = None
        if emergency.location_address_status != "reported" and emergency.location_address_status != "unknown":
            emergency.location_address_status = (
                "pending"
                if emergency.latitude is not None and emergency.longitude is not None
                else "unavailable"
            )

    if "transcription" in updates and updates["transcription"] and not emergency.text_content:
        emergency.text_content = updates["transcription"]
    if "transcription" in updates and updates["transcription"] and emergency.status == "pending_transcription":
        emergency.status = "received"

    try:
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to update emergency call: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc

    _schedule_location_address(background_tasks, emergency)
    return emergency


@router.get("/{call_id}/audio", name="get_emergency_audio_file")
async def get_emergency_audio_file(
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    emergency = await db.get(EmergencyCall, call_id)
    if not emergency or not emergency.audio_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

    path = BASE_DIR / emergency.audio_file_path
    if not path.exists():
        # Also try absolute-style path under storage
        alt = UPLOAD_DIR / Path(emergency.audio_file_path).name
        if alt.exists():
            path = alt
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing on disk")

    return FileResponse(
        path,
        media_type=emergency.audio_content_type or "application/octet-stream",
        filename=emergency.original_audio_filename or path.name,
    )


@router.post("/{call_id}/map-snapshot", response_model=EmergencyCallOut, name="attach_emergency_map_snapshot")
async def attach_emergency_map_snapshot(
    call_id: uuid.UUID,
    request: Request,
    map_snapshot: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    emergency = await db.get(EmergencyCall, call_id)
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency call not found")
    relative_path, filename, content_type, size = await _save_map_snapshot(map_snapshot)
    emergency.map_snapshot_file_path = relative_path
    emergency.map_snapshot_filename = filename
    emergency.map_snapshot_content_type = content_type
    emergency.map_snapshot_size = size
    emergency.map_snapshot_url = str(
        request.url_for("get_emergency_map_snapshot", call_id=emergency.id)
    )
    try:
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to persist map snapshot metadata: %s", exc)
        raise HTTPException(status_code=503, detail="Emergency storage is temporarily unavailable") from exc
    return emergency


@router.get("/{call_id}/map-snapshot", name="get_emergency_map_snapshot")
async def get_emergency_map_snapshot(
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    emergency = await db.get(EmergencyCall, call_id)
    if not emergency or not emergency.map_snapshot_file_path:
        raise HTTPException(status_code=404, detail="Map snapshot not found")
    snapshot_path = resolve_map_snapshot_path(emergency.map_snapshot_file_path)
    if snapshot_path is None:
        raise HTTPException(status_code=404, detail="Map snapshot file missing on disk")
    return FileResponse(
        snapshot_path,
        media_type=emergency.map_snapshot_content_type or "image/png",
        filename=emergency.map_snapshot_filename or snapshot_path.name,
    )
