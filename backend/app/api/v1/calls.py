from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()

class CallCreate(BaseModel):
    caller_number: str
    location: str | None = None
    audio_reference: str | None = None
    priority: str | None = "low"

class CallOut(CallCreate):
    id: int
    created_at: datetime

_calls: List[dict] = []
_next_id = 1

@router.post("/", response_model=CallOut)
async def create_call(payload: CallCreate):
    global _next_id
    record = payload.dict()
    record.update({"id": _next_id, "created_at": datetime.utcnow()})
    _calls.append(record)
    _next_id += 1
    return record

@router.get("/", response_model=List[CallOut])
async def list_calls():
    return _calls

@router.get("/{call_id}", response_model=CallOut)
async def get_call(call_id: int):
    for c in _calls:
        if c["id"] == call_id:
            return c
    raise HTTPException(status_code=404, detail="Call not found")
