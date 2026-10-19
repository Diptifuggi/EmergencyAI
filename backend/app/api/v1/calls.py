from __future__ import annotations

from datetime import datetime
from typing import Any, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.emergency_call import EmergencyCall

router = APIRouter()


class CallCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    caller_number: str | None = None
    caller_name: str | None = None
    location: str | None = None
    audio_reference: str | None = None
    priority: str | None = "normal"
    text_content: str | None = None


class CallOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    caller_number: str | None = None
    caller_name: str | None = None
    location: str | None = None
    audio_reference: str | None = None
    priority: str = "normal"
    status: str = "received"
    category: str | None = None
    created_at: datetime


def _map_to_call_out(call: EmergencyCall) -> CallOut:
    meta = call.client_metadata or {}
    if not isinstance(meta, dict):
        meta = {}
    analysis = meta.get("emergency_analysis", {}).get("analysis", {}) if isinstance(meta.get("emergency_analysis"), dict) else {}
    cat = analysis.get("emergency_type") or call.call_type
    if cat:
        cat = str(cat).replace("_", " ").title()

    return CallOut(
        id=str(call.id),
        caller_number=meta.get("caller_phone") or (str(call.user_id) if call.user_id else None),
        caller_name=meta.get("caller_name"),
        location=call.location_address or (f"{call.latitude}, {call.longitude}" if call.latitude is not None else None),
        audio_reference=call.audio_url or call.audio_file_path,
        priority=call.priority or "normal",
        status=call.status or "received",
        category=cat,
        created_at=call.created_at,
    )


@router.post("/", response_model=CallOut, status_code=status.HTTP_201_CREATED)
async def create_call(payload: CallCreate, db: AsyncSession = Depends(get_db)) -> CallOut:
    meta = {
        "caller_phone": payload.caller_number,
        "caller_name": payload.caller_name,
        "source": "api_calls",
    }
    emergency = EmergencyCall(
        call_type="manual" if not payload.audio_reference else "audio",
        text_content=payload.text_content,
        priority=payload.priority or "normal",
        status="received",
        location_address=payload.location,
        audio_file_path=payload.audio_reference,
        client_metadata=meta,
    )
    db.add(emergency)
    await db.commit()
    await db.refresh(emergency)
    return _map_to_call_out(emergency)


@router.get("/", response_model=List[CallOut])
async def list_calls(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[CallOut]:
    result = await db.execute(
        select(EmergencyCall).order_by(EmergencyCall.created_at.desc()).offset(offset).limit(limit)
    )
    calls = result.scalars().all()
    return [_map_to_call_out(c) for c in calls]


@router.get("/{call_id}", response_model=CallOut)
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)) -> CallOut:
    try:
        call_uuid = uuid.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    emergency = await db.get(EmergencyCall, call_uuid)
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    return _map_to_call_out(emergency)


@router.patch("/{call_id}", response_model=CallOut)
async def update_call(call_id: str, payload: dict[str, Any], db: AsyncSession = Depends(get_db)) -> CallOut:
    try:
        call_uuid = uuid.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    emergency = await db.get(EmergencyCall, call_uuid)
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    for field in ("status", "priority", "transcription", "text_content", "language"):
        if field in payload and payload[field] is not None:
            setattr(emergency, field, payload[field])

    await db.commit()
    await db.refresh(emergency)
    return _map_to_call_out(emergency)
