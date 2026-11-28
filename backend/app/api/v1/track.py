from __future__ import annotations

import logging
import math
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import async_session, get_db
from ...core.dependencies import OPERATOR_ROLES, get_current_citizen, get_current_operator
from ...core.rate_limit import sos_rate_limiter
from ...core.security import decode_token
from ...core.ws_manager import ws_manager
from ...models.track_session import TrackPoint, TrackSession, TrackSessionStatus
from ...models.user import User
from ...models.user_notification import UserNotification
from ...models.user_profile import UserProfile
from ...schemas.sos import (
    TrackAttachSOSRequest,
    TrackPointBatchCreate,
    TrackPointCreate,
    TrackPointOut,
    TrackSessionOut,
    TrackStartRequest,
)
from ...schemas.v1 import UserOut
from ...services.auth_service import AuthService
from .audit import record_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _compute_distance_meters(points: list[TrackPoint]) -> float:
    if len(points) < 2:
        return 0.0
    ordered = sorted(points, key=lambda p: p.recorded_at)
    total = 0.0
    for i in range(1, len(ordered)):
        total += _haversine_meters(
            ordered[i - 1].latitude,
            ordered[i - 1].longitude,
            ordered[i].latitude,
            ordered[i].longitude,
        )
    return round(total, 1)


def _validate_point_timestamp(recorded_at: datetime | None, now: datetime) -> datetime:
    if recorded_at is None:
        return now
    ts = recorded_at if recorded_at.tzinfo else recorded_at.replace(tzinfo=timezone.utc)
    if ts > now + timedelta(minutes=5):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Point timestamp cannot be far in the future.",
        )
    return ts


@router.post("/start", response_model=TrackSessionOut, status_code=status.HTTP_201_CREATED)
async def start_track_session(
    payload: TrackStartRequest,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> TrackSessionOut:
    sos_rate_limiter.check_rate_limit(f"track_start_{current_user.id}", max_requests=10, window_seconds=60.0)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=payload.duration_hours)
    share_token = secrets.token_urlsafe(32)

    session = TrackSession(
        user_id=current_user.id,
        share_token=share_token,
        duration_hours=payload.duration_hours,
        share_with_control_room=payload.share_with_control_room,
        sos_alert_id=payload.sos_alert_id,
        status=TrackSessionStatus.ACTIVE.value,
        started_at=now,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()

    points = []
    if payload.latitude is not None and payload.longitude is not None:
        pt = TrackPoint(
            session_id=session.id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_m,
            battery_pct=payload.battery_pct,
            recorded_at=now,
        )
        db.add(pt)
        points.append(pt)

    await db.commit()
    await db.refresh(session)
    if points:
        await db.refresh(points[0])

    logger.info(f"TrackMe session started id={session.id} duration_hours={payload.duration_hours}")
    return TrackSessionOut(
        id=session.id,
        share_token=session.share_token,
        duration_hours=session.duration_hours,
        share_with_control_room=session.share_with_control_room,
        sos_alert_id=session.sos_alert_id,
        status=session.status,
        started_at=session.started_at,
        expires_at=session.expires_at,
        ended_at=session.ended_at,
        distance_meters=0.0,
        points=[TrackPointOut.model_validate(p) for p in points],
    )


@router.post("/{session_id}/points", response_model=List[TrackPointOut])
async def add_track_points(
    session_id: UUID,
    payload: Union[TrackPointBatchCreate, TrackPointCreate],
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> List[TrackPointOut]:
    sos_rate_limiter.check_min_interval(f"track_pt_{session_id}", min_interval_seconds=2.0)

    session = await db.get(TrackSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Track session not found")

    now = datetime.now(timezone.utc)
    if session.status != TrackSessionStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Track session is not active")

    if session.expires_at <= now:
        session.status = TrackSessionStatus.EXPIRED.value
        session.ended_at = session.expires_at
        db.add(
            UserNotification(
                user_id=current_user.id,
                notification_type="track_expired",
                title="TrackMe Session Expired",
                message="Your live location sharing session has expired.",
            )
        )
        await db.commit()
        raise HTTPException(status_code=400, detail="Track session has expired")

    incoming = payload.points if isinstance(payload, TrackPointBatchCreate) else [payload]

    # Preload existing client_point_ids for duplicate-safe batching
    client_ids = [p.client_point_id for p in incoming if p.client_point_id]
    existing_ids: set[str] = set()
    if client_ids:
        ex_stmt = select(TrackPoint.client_point_id).where(
            TrackPoint.session_id == session.id,
            TrackPoint.client_point_id.in_(client_ids),
        )
        existing_ids = {row[0] for row in (await db.execute(ex_stmt)).all() if row[0]}

    created_points: list[TrackPoint] = []
    for item in incoming:
        ts = _validate_point_timestamp(item.recorded_at, now)
        if item.client_point_id and item.client_point_id in existing_ids:
            continue
        if item.client_point_id:
            existing_ids.add(item.client_point_id)
        pt = TrackPoint(
            session_id=session.id,
            client_point_id=item.client_point_id,
            latitude=item.latitude,
            longitude=item.longitude,
            accuracy_m=item.accuracy_m,
            battery_pct=item.battery_pct,
            recorded_at=ts,
        )
        db.add(pt)
        created_points.append(pt)

    await db.commit()
    for pt in created_points:
        await db.refresh(pt)

    if created_points:
        latest = created_points[-1]
        event_payload = {
            "event": "track.updated",
            "session_id": str(session.id),
            "share_token": session.share_token,
            "sos_alert_id": str(session.sos_alert_id) if session.sos_alert_id else None,
            "last_position": {
                "latitude": latest.latitude,
                "longitude": latest.longitude,
                "accuracy_m": latest.accuracy_m,
                "recorded_at": latest.recorded_at.isoformat(),
            },
            "status": session.status,
        }
        await ws_manager.broadcast(f"track:{session.share_token}", event_payload)
        if session.share_with_control_room or session.sos_alert_id:
            await ws_manager.broadcast("operator", event_payload)

    return [TrackPointOut.model_validate(p) for p in created_points]


@router.post("/{session_id}/attach-sos", response_model=TrackSessionOut)
async def attach_sos_to_track(
    session_id: UUID,
    payload: TrackAttachSOSRequest,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> TrackSessionOut:
    session = await db.get(TrackSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Track session not found")

    session.sos_alert_id = payload.sos_alert_id
    await db.commit()
    await db.refresh(session)

    await ws_manager.broadcast(
        "operator",
        {
            "event": "track.updated",
            "session_id": str(session.id),
            "sos_alert_id": str(session.sos_alert_id),
            "status": session.status,
        },
    )

    return TrackSessionOut(
        id=session.id,
        share_token=session.share_token,
        duration_hours=session.duration_hours,
        share_with_control_room=session.share_with_control_room,
        sos_alert_id=session.sos_alert_id,
        status=session.status,
        started_at=session.started_at,
        expires_at=session.expires_at,
        ended_at=session.ended_at,
        distance_meters=0.0,
        points=[],
    )


@router.post("/{session_id}/stop", response_model=TrackSessionOut)
async def stop_track_session(
    session_id: UUID,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> TrackSessionOut:
    session = await db.get(TrackSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Track session not found")

    now = datetime.now(timezone.utc)
    if session.status == TrackSessionStatus.ACTIVE.value:
        session.status = TrackSessionStatus.ENDED.value
        session.ended_at = now
        await db.commit()
        await db.refresh(session)

    pts_stmt = (
        select(TrackPoint)
        .where(TrackPoint.session_id == session.id)
        .order_by(TrackPoint.recorded_at.desc())
        .limit(100)
    )
    pts = (await db.execute(pts_stmt)).scalars().all()
    stop_payload = {
        "event": "track.updated",
        "session_id": str(session.id),
        "status": session.status,
    }
    await ws_manager.broadcast(f"track:{session.share_token}", stop_payload)
    if session.share_with_control_room or session.sos_alert_id:
        await ws_manager.broadcast("operator", stop_payload)

    return TrackSessionOut(
        id=session.id,
        share_token=session.share_token,
        duration_hours=session.duration_hours,
        share_with_control_room=session.share_with_control_room,
        sos_alert_id=session.sos_alert_id,
        status=session.status,
        started_at=session.started_at,
        expires_at=session.expires_at,
        ended_at=session.ended_at,
        distance_meters=_compute_distance_meters(list(pts)),
        points=[TrackPointOut.model_validate(p) for p in pts],
    )


# --- Operator TrackMe Endpoints (MUST precede /{session_id}) ---

@router.get("/operator/active")
async def list_operator_track_sessions(
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TrackSession)
        .where(
            or_(
                TrackSession.share_with_control_room.is_(True),
                TrackSession.sos_alert_id.is_not(None),
            )
        )
        .order_by(TrackSession.started_at.desc())
        .limit(50)
    )
    sessions = (await db.execute(stmt)).scalars().all()
    now = datetime.now(timezone.utc)
    out = []
    for s in sessions:
        if s.status == TrackSessionStatus.ACTIVE.value and s.expires_at <= now:
            s.status = TrackSessionStatus.EXPIRED.value
            s.ended_at = s.expires_at
        prof_name = (
            await db.execute(select(UserProfile.full_name).where(UserProfile.user_id == s.user_id))
        ).scalar_one_or_none()
        if not prof_name:
            prof_name = (
                await db.execute(select(User.username).where(User.id == s.user_id))
            ).scalar_one_or_none()
        last_pt = (
            await db.execute(
                select(TrackPoint)
                .where(TrackPoint.session_id == s.id)
                .order_by(TrackPoint.recorded_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        out.append({
            "id": str(s.id),
            "user_id": str(s.user_id),
            "user_name": prof_name or "Citizen",
            "status": s.status,
            "duration_hours": s.duration_hours,
            "share_with_control_room": s.share_with_control_room,
            "sos_alert_id": str(s.sos_alert_id) if s.sos_alert_id else None,
            "started_at": s.started_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "last_position": {
                "latitude": last_pt.latitude,
                "longitude": last_pt.longitude,
                "accuracy_m": last_pt.accuracy_m,
                "recorded_at": last_pt.recorded_at.isoformat(),
            } if last_pt else None,
        })
    await db.commit()
    return {"items": out}


@router.get("/operator/{session_id}")
async def get_operator_track_detail(
    session_id: UUID,
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(TrackSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Track session not found")

    if not session.share_with_control_room and not session.sos_alert_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has not shared this TrackMe session with the control room.",
        )

    now = datetime.now(timezone.utc)
    if session.status == TrackSessionStatus.ACTIVE.value and session.expires_at <= now:
        session.status = TrackSessionStatus.EXPIRED.value
        session.ended_at = session.expires_at

    pts = (
        await db.execute(
            select(TrackPoint)
            .where(TrackPoint.session_id == session.id)
            .order_by(TrackPoint.recorded_at.asc())
            .limit(500)
        )
    ).scalars().all()

    record_audit_log(
        db,
        current_user,
        "track_session_viewed",
        "track_session",
        str(session.id),
    )
    await db.commit()

    return {
        "id": str(session.id),
        "user_id": str(session.user_id),
        "share_token": session.share_token,
        "duration_hours": session.duration_hours,
        "share_with_control_room": session.share_with_control_room,
        "sos_alert_id": str(session.sos_alert_id) if session.sos_alert_id else None,
        "status": session.status,
        "started_at": session.started_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "distance_meters": _compute_distance_meters(list(pts)),
        "points": [TrackPointOut.model_validate(p).model_dump(mode="json") for p in pts],
    }


@router.websocket("/ws/operator")
async def operator_track_ws(
    websocket: WebSocket,
    token: str = Query(...),
):
    try:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            await websocket.close(code=1008)
            return
        async with async_session() as db:
            user = await AuthService.get_user_by_id(db, str(payload.get("sub")))
            if not user or not user.is_active or (user.role_name or "").lower() not in OPERATOR_ROLES:
                await websocket.close(code=1008)
                return
    except Exception:
        await websocket.close(code=1008)
        return

    await ws_manager.connect("operator", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("operator", websocket)


@router.get("/{session_id}", response_model=TrackSessionOut)
async def get_track_session(
    session_id: UUID,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> TrackSessionOut:
    session = await db.get(TrackSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Track session not found")

    now = datetime.now(timezone.utc)
    if session.status == TrackSessionStatus.ACTIVE.value and session.expires_at <= now:
        session.status = TrackSessionStatus.EXPIRED.value
        session.ended_at = session.expires_at
        await db.commit()
        await db.refresh(session)

    pts_stmt = (
        select(TrackPoint)
        .where(TrackPoint.session_id == session.id)
        .order_by(TrackPoint.recorded_at.desc())
        .limit(100)
    )
    pts = (await db.execute(pts_stmt)).scalars().all()
    return TrackSessionOut(
        id=session.id,
        share_token=session.share_token,
        duration_hours=session.duration_hours,
        share_with_control_room=session.share_with_control_room,
        sos_alert_id=session.sos_alert_id,
        status=session.status,
        started_at=session.started_at,
        expires_at=session.expires_at,
        ended_at=session.ended_at,
        distance_meters=_compute_distance_meters(list(pts)),
        points=[TrackPointOut.model_validate(p) for p in pts],
    )
