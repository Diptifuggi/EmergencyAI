from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import BASE_DIR, settings
from ...core.database import get_db
from ...core.exceptions import FileTooLargeError, InvalidFileTypeError
from ...core.logger import get_logger
from ...models.emergency_call import EmergencyCall
from ...schemas.emergency_call import (
    EmergencyCallListOut,
    EmergencyCallOut,
    EmergencyCallTextCreate,
    EmergencyCallUpdate,
)
from ...services.emergency_call_analysis_runner import run_post_create_analysis
from ...services.location_service import reverse_geocode


router = APIRouter()
logger = get_logger("app.api.v1.emergency_calls")

UPLOAD_DIR = BASE_DIR / "backend" / "storage" / "audio"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAP_SNAPSHOT_DIR = BASE_DIR / "backend" / "storage" / "map_snapshots"
MAP_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


async def _location_address(latitude: float | None, longitude: float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return await reverse_geocode(latitude, longitude)


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
            stderr = (completed.stderr or "").strip()
            logger.warning(
                "Audio conversion failed filename=%s inputBytes=%d: %s",
                original_filename,
                len(audio_bytes),
                stderr or "unknown ffmpeg error",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio is not a valid or supported recording",
            )

        converted_bytes = output_path.read_bytes()
        if not converted_bytes:
            logger.warning("Audio conversion produced empty output filename=%s inputBytes=%d", original_filename, len(audio_bytes))
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
        "Audio upload received filename=%s contentType=%s bytes=%d field=file",
        filename,
        file.content_type or "unknown",
        len(contents),
    )
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio is empty. Please record again.",
        )
    if ext == ".mp3" and not _looks_like_mp3(contents):
        logger.warning("Audio upload rejected invalid MP3 filename=%s bytes=%d", filename, len(contents))
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
        logger.warning("Audio conversion produced invalid MP3 filename=%s bytes=%d", filename, len(converted_bytes))
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
        "Audio upload stored filename=%s receivedBytes=%d writtenBytes=%d finalPath=%s",
        filename,
        len(contents),
        len(converted_bytes),
        relative_path,
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
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    emergency = EmergencyCall(
        call_type="text",
        text_content=payload.text,
        language=payload.language,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_accuracy=payload.location_accuracy,
        location_timestamp=payload.location_timestamp,
        location_address=await _location_address(payload.latitude, payload.longitude),
        location_status=_location_status(payload.latitude, payload.longitude),
        source=payload.source,
        priority=payload.priority,
        client_metadata=payload.client_metadata,
        status="received",
    )

    try:
        db.add(emergency)
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to persist text emergency: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc

    return await run_post_create_analysis(db, emergency)


@router.post("/audio", response_model=EmergencyCallOut, status_code=status.HTTP_201_CREATED)
async def create_audio_emergency(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(...),
    transcription: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    location_accuracy: float | None = Form(None),
    location_timestamp: str | None = Form(None),
    source: str = Form("flutter"),
    priority: str = Form("normal"),
    client_metadata: str | None = Form(None),
    map_snapshot: UploadFile | None = File(None),
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
    _validate_coordinates(latitude, longitude, location_accuracy)
    relative_path, original_name, content_type, size_bytes = await _save_audio_file(file)
    snapshot_data = await _save_map_snapshot(map_snapshot) if map_snapshot else None
    meta = _parse_metadata(client_metadata)
    cleaned_transcription = (transcription or "").strip() or None
    cleaned_language = language.strip()
    if not cleaned_language:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="language must not be empty",
        )

    status_value = "received" if cleaned_transcription else "pending_transcription"
    emergency = EmergencyCall(
        call_type="audio",
        language=cleaned_language,
        status=status_value,
        priority=(priority or "normal").strip() or "normal",
        audio_file_path=relative_path,
        original_audio_filename=original_name,
        audio_content_type=content_type,
        audio_file_size=size_bytes,
        transcription=cleaned_transcription,
        text_content=cleaned_transcription,
        source=(source or "flutter").strip() or "flutter",
        client_metadata=meta,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=location_accuracy,
        location_timestamp=_parse_location_timestamp(location_timestamp),
        location_address=await _location_address(latitude, longitude),
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
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to persist audio emergency metadata: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc

    return await run_post_create_analysis(db, emergency)


@router.post(
    "/voice-text",
    response_model=EmergencyCallOut,
    status_code=status.HTTP_201_CREATED,
    summary="Store voice + text together (Flutter primary endpoint)",
)
async def create_voice_and_text_emergency(
    request: Request,
    file: UploadFile = File(...),
    transcription: str = Form(...),
    language: str = Form(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    location_accuracy: float | None = Form(None),
    location_timestamp: str | None = Form(None),
    source: str = Form("flutter"),
    priority: str = Form("normal"),
    client_metadata: str | None = Form(None),
    map_snapshot: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    """Requires both audio file and its text. Prefer this from the Flutter app."""
    _validate_coordinates(latitude, longitude, location_accuracy)
    cleaned = transcription.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="transcription must not be empty",
        )

    relative_path, original_name, content_type, size_bytes = await _save_audio_file(file)
    snapshot_data = await _save_map_snapshot(map_snapshot) if map_snapshot else None
    meta = _parse_metadata(client_metadata)

    emergency = EmergencyCall(
        call_type="voice_text",
        language=language.strip(),
        status="received",
        priority=(priority or "normal").strip() or "normal",
        audio_file_path=relative_path,
        original_audio_filename=original_name,
        audio_content_type=content_type,
        audio_file_size=size_bytes,
        transcription=cleaned,
        text_content=cleaned,
        source=(source or "flutter").strip() or "flutter",
        client_metadata=meta,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=location_accuracy,
        location_timestamp=_parse_location_timestamp(location_timestamp),
        location_address=await _location_address(latitude, longitude),
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
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to persist voice+text emergency: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency storage is temporarily unavailable",
        ) from exc

    return await run_post_create_analysis(db, emergency)


@router.get("/", response_model=EmergencyCallListOut)
async def list_emergency_calls(
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
    db: AsyncSession = Depends(get_db),
) -> EmergencyCall:
    """Update transcription/status/metadata later without breaking clients."""
    emergency = await db.get(EmergencyCall, call_id)
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency call not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(emergency, key, value)

    if "latitude" in updates or "longitude" in updates:
        emergency.location_status = _location_status(emergency.latitude, emergency.longitude)

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
    snapshot_path = BASE_DIR / emergency.map_snapshot_file_path
    if not snapshot_path.exists():
        snapshot_path = MAP_SNAPSHOT_DIR / Path(emergency.map_snapshot_file_path).name
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="Map snapshot file missing on disk")
    return FileResponse(
        snapshot_path,
        media_type=emergency.map_snapshot_content_type or "image/png",
        filename=emergency.map_snapshot_filename or snapshot_path.name,
    )
