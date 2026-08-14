from typing import List
from fastapi import APIRouter, Depends, status
from app.schemas.v1 import CallOut

router = APIRouter(tags=["calls"])


def _get_current_user():
    """Auth dependency placeholder."""
    return None


@router.get("/", response_model=List[CallOut], status_code=status.HTTP_200_OK)
async def list_calls(current_user=Depends(_get_current_user)):
    """Placeholder calls listing."""
    return []


@router.get("/{call_id}", response_model=CallOut, status_code=status.HTTP_200_OK)
async def get_call(call_id: str, current_user=Depends(_get_current_user)):
    """Return a sample call by id (placeholder)."""
    # sample data — in real app this would fetch from DB
    return {
        "id": call_id,
        "started_at": None,
        "duration_seconds": None,
    }


@router.post("/", response_model=CallOut, status_code=status.HTTP_201_CREATED)
async def create_call(payload: dict, current_user=Depends(_get_current_user)):
    """Create a new call (development stub). Returns created call with id."""
    import uuid
    cid = str(uuid.uuid4())
    return {
        "id": cid,
        "started_at": payload.get("started_at"),
        "duration_seconds": payload.get("duration_seconds") or 0,
    }


@router.post("/pipeline/run/{call_id}")
async def run_pipeline(call_id: str, current_user=Depends(_get_current_user)):
    """Stub to trigger pipeline processing for a call."""
    # in a real system this would enqueue background work
    return {"status": "started", "call_id": call_id}
