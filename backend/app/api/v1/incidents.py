from __future__ import annotations

from datetime import datetime
from typing import Any, List
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.emergency_call import EmergencyCall
from .emergency_calls import _resolve_location_address_background

router = APIRouter()


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    description: str | None = None
    severity: str | int | float = "low"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_address: str | None = Field(default=None, max_length=1000)


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
    location_address_status: str = "unavailable"
    location_status: str = "unavailable"
    call_count: int = 1
    created_at: datetime


def _map_to_incident_out(call: EmergencyCall) -> IncidentOut:
    meta = call.client_metadata or {}
    if not isinstance(meta, dict):
        meta = {}
    analysis_payload = meta.get("emergency_analysis")
    if not isinstance(analysis_payload, dict):
        analysis_payload = {}
    analysis = analysis_payload.get("analysis")
    if not isinstance(analysis, dict):
        analysis = analysis_payload

    raw_cat = analysis.get("emergency_type") or "Not reported"
    cat_title = str(raw_cat).replace("_", " ").title()

    title = str(meta.get("incident_title") or f"{cat_title} Emergency")
    if call.location_address:
        loc_preview = call.location_address[:45]
        if not meta.get("incident_title"):
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
        severity=score if isinstance(score, (int, float)) else None,
        priority=priority_level,
        status=status_val,
        latitude=call.latitude,
        longitude=call.longitude,
        location_address=call.location_address,
        location_address_status=getattr(call, "location_address_status", "unavailable"),
        location_status=getattr(call, "location_status", "unavailable"),
        call_count=1,
        created_at=call.created_at,
    )


@router.post("/", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IncidentOut:
    reported_address = payload.location_address.strip() if payload.location_address else None
    has_coordinates = payload.latitude is not None and payload.longitude is not None
    emergency = EmergencyCall(
        call_type="incident",
        text_content=payload.description or payload.title,
        priority=str(payload.severity).lower() if isinstance(payload.severity, str) else "normal",
        status="received",
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_address=reported_address or None,
        location_address_status=(
            "reported" if reported_address else "pending" if has_coordinates else "unavailable"
        ),
        client_metadata={"incident_title": payload.title, "source": "api_incidents"},
    )
    db.add(emergency)
    await db.commit()
    await db.refresh(emergency)
    if (
        payload.latitude is not None
        and payload.longitude is not None
        and not reported_address
    ):
        background_tasks.add_task(
            _resolve_location_address_background,
            emergency.id,
            emergency.latitude,
            emergency.longitude,
        )
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

    result = await db.execute(
        select(EmergencyCall)
        .where(EmergencyCall.id == call_uuid)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    emergency = result.scalar_one_or_none()
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

    result = await db.execute(
        select(EmergencyCall)
        .where(EmergencyCall.id == call_uuid)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    emergency = result.scalar_one_or_none()
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
