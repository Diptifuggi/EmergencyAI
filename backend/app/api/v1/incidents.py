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


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    description: str | None = None
    severity: str | int | float = "low"
    latitude: float | None = None
    longitude: float | None = None


class IncidentOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    description: str | None = None
    incident_type: str | None = None
    severity: int | float | str | None = None
    priority: str | None = None
    status: str = "Open"
    latitude: float | None = None
    longitude: float | None = None
    location_address: str | None = None
    call_count: int = 1
    created_at: datetime


def _map_to_incident_out(call: EmergencyCall) -> IncidentOut:
    meta = call.client_metadata or {}
    if not isinstance(meta, dict):
        meta = {}
    analysis = meta.get("emergency_analysis", {}).get("analysis", {}) if isinstance(meta.get("emergency_analysis"), dict) else {}

    raw_cat = analysis.get("emergency_type") or call.call_type or "Emergency"
    cat_title = str(raw_cat).replace("_", " ").title()

    title = f"{cat_title} Emergency"
    if call.location_address:
        loc_preview = call.location_address[:45]
        title = f"{cat_title} near {loc_preview}"

    priority_level = analysis.get("priority_level") or call.priority or "Moderate"
    priority_level = str(priority_level).title()
    score = analysis.get("priority_score")

    status_val = "Resolved" if str(call.status or "").lower() == "resolved" else "Open"

    return IncidentOut(
        id=str(call.id),
        title=title,
        description=call.text_content or call.transcription or f"{cat_title} report registered.",
        incident_type=cat_title,
        severity=score if score is not None else 50,
        priority=priority_level,
        status=status_val,
        latitude=call.latitude,
        longitude=call.longitude,
        location_address=call.location_address,
        call_count=1,
        created_at=call.created_at,
    )


@router.post("/", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
async def create_incident(payload: IncidentCreate, db: AsyncSession = Depends(get_db)) -> IncidentOut:
    emergency = EmergencyCall(
        call_type="incident",
        text_content=payload.description or payload.title,
        priority=str(payload.severity).lower() if isinstance(payload.severity, str) else "normal",
        status="received",
        latitude=payload.latitude,
        longitude=payload.longitude,
        client_metadata={"incident_title": payload.title, "source": "api_incidents"},
    )
    db.add(emergency)
    await db.commit()
    await db.refresh(emergency)
    return _map_to_incident_out(emergency)


@router.get("/", response_model=List[IncidentOut])
async def list_incidents(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> List[IncidentOut]:
    result = await db.execute(
        select(EmergencyCall).order_by(EmergencyCall.created_at.desc()).offset(offset).limit(limit)
    )
    calls = result.scalars().all()
    return [_map_to_incident_out(c) for c in calls]


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)) -> IncidentOut:
    try:
        call_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    emergency = await db.get(EmergencyCall, call_uuid)
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    return _map_to_incident_out(emergency)


@router.patch("/{incident_id}/close", response_model=IncidentOut)
async def close_incident(incident_id: str, db: AsyncSession = Depends(get_db)) -> IncidentOut:
    try:
        call_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    emergency = await db.get(EmergencyCall, call_uuid)
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    emergency.status = "resolved"
    await db.commit()
    await db.refresh(emergency)
    return _map_to_incident_out(emergency)


@router.post("/{incident_id}/dispatch", response_model=dict[str, Any])
async def create_dispatch(incident_id: str, payload: dict[str, Any], db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        call_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    emergency = await db.get(EmergencyCall, call_uuid)
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    meta = dict(emergency.client_metadata or {})
    dispatches = list(meta.get("dispatches", []))
    dispatches.append({
        "timestamp": datetime.utcnow().isoformat(),
        "details": payload,
    })
    meta["dispatches"] = dispatches
    emergency.client_metadata = meta
    emergency.status = "assigned"

    await db.commit()
    await db.refresh(emergency)
    return {"status": "success", "incident_id": incident_id, "dispatched": payload}
