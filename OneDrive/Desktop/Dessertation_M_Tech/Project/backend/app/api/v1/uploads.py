from fastapi import APIRouter, UploadFile, File, HTTPException
from ...core.config import settings
from ...core.exceptions import FileTooLargeError, InvalidFileTypeError
import os
from pathlib import Path

router = APIRouter()

UPLOAD_DIR = Path("backend/storage")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/audio")
async def upload_audio(file: UploadFile = File(...)):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise InvalidFileTypeError(f"Extension {ext} not allowed")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise FileTooLargeError("File exceeds maximum allowed size")

    dest = UPLOAD_DIR / filename
    with open(dest, "wb") as f:
        f.write(contents)

    return {"filename": filename, "size_mb": round(size_mb, 2)}
