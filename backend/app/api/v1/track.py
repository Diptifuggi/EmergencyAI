from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.dependencies import get_current_citizen
from ...core.rate_limit import sos_rate_limiter
from ...models.track_session import TrackPoint, TrackSession, TrackSessionStatus
from ...models.user_notification import UserNotification
from ...schemas.sos import (
    TrackPointCreate,
    TrackPointOut,
    TrackSessionOut,
    TrackStartRequest,
)
from ...schemas.v1 import UserOut

logger = logging.getLogger(__name__)

router = APIRouter()


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
        status=session.status,
        started_at=session.started_at,
        expires_at=session.expires_at,
        ended_at=session.ended_at,
        points=[TrackPointOut.model_validate(p) for p in points],
    )


@router.post("/{session_id}/points", response_model=TrackPointOut)
async def add_track_point(
    session_id: UUID,
    payload: TrackPointCreate,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> TrackPointOut:
    sos_rate_limiter.check_min_interval(f"track_pt_{session_id}", min_interval_seconds=5.0)

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

    pt = TrackPoint(
        session_id=session.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
        battery_pct=payload.battery_pct,
        recorded_at=now,
    )
    db.add(pt)
    await db.commit()
    await db.refresh(pt)
    return TrackPointOut.model_validate(pt)


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
        .limit(50)
    )
    pts = (await db.execute(pts_stmt)).scalars().all()
    return TrackSessionOut(
        id=session.id,
        share_token=session.share_token,
        duration_hours=session.duration_hours,
        status=session.status,
        started_at=session.started_at,
        expires_at=session.expires_at,
        ended_at=session.ended_at,
        points=[TrackPointOut.model_validate(p) for p in pts],
    )


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
        .limit(50)
    )
    pts = (await db.execute(pts_stmt)).scalars().all()
    return TrackSessionOut(
        id=session.id,
        share_token=session.share_token,
        duration_hours=session.duration_hours,
        status=session.status,
        started_at=session.started_at,
        expires_at=session.expires_at,
        ended_at=session.ended_at,
        points=[TrackPointOut.model_validate(p) for p in pts],
    )
