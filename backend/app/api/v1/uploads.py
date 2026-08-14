from fastapi import APIRouter, UploadFile, File, Depends, status
from app.schemas.v1 import UploadOut

router = APIRouter(tags=["uploads"])


def _get_current_user():
    """Auth dependency placeholder."""
    return None


@router.post("/", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...), current_user=Depends(_get_current_user)):
    """Placeholder uploads endpoint."""
    return UploadOut(filename=file.filename, content_type=file.content_type)


@router.post("/audio/{call_id}")
async def upload_call_audio(call_id: str, file: UploadFile = File(...), current_user=Depends(_get_current_user)):
    """Accept audio for a call (development stub)."""
    # just echo back filename and pretend URL
    return {"call_id": call_id, "filename": file.filename, "url": f"/media/{file.filename}"}


@router.get("/status/{call_id}")
async def upload_status(call_id: str, current_user=Depends(_get_current_user)):
    """Return fake pipeline/upload status for a call."""
    # rotate through statuses based on last digit
    status_map = ["Processing","Transcribing","Classifying","Scored"]
    idx = ord(call_id[-1]) % len(status_map) if call_id else 0
    return {"call_id": call_id, "status": status_map[idx]}
