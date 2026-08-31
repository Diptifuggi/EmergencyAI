from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()

class IncidentCreate(BaseModel):
    title: str
    description: str | None = None
    severity: str = "low"

class IncidentOut(IncidentCreate):
    id: int
    created_at: datetime

_incidents: List[dict] = []
_next_id = 1

@router.post("/", response_model=IncidentOut)
async def create_incident(payload: IncidentCreate):
    global _next_id
    record = payload.dict()
    record.update({"id": _next_id, "created_at": datetime.utcnow()})
    _incidents.append(record)
    _next_id += 1
    return record

@router.get("/", response_model=List[IncidentOut])
async def list_incidents():
    return _incidents

@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: int):
    for i in _incidents:
        if i["id"] == incident_id:
            return i
    raise HTTPException(status_code=404, detail="Incident not found")
