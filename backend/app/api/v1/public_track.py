from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import sos_rate_limiter
from ...core.ws_manager import ws_manager
from ...models.track_session import TrackPoint, TrackSession, TrackSessionStatus
from ...models.user import User
from ...models.user_profile import UserProfile
from ...schemas.sos import PublicTrackOut, PublicTrackPosition

router = APIRouter()


@router.get("/track/{token}", response_model=PublicTrackOut)
async def get_public_track_session(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PublicTrackOut:
    client_ip = request.client.host if request.client else "unknown"
    sos_rate_limiter.check_rate_limit(f"public_track_{client_ip}", max_requests=30, window_seconds=60.0)

    stmt = select(TrackSession).where(TrackSession.share_token == token)
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Tracking session not found")

    now = datetime.now(timezone.utc)
    if session.status == TrackSessionStatus.ACTIVE.value and session.expires_at <= now:
        session.status = TrackSessionStatus.EXPIRED.value
        session.ended_at = session.expires_at
        await db.commit()
        await db.refresh(session)

    # Fetch only first name (no phone, address, or medical info)
    first_name = None
    profile_stmt = select(UserProfile.full_name).where(UserProfile.user_id == session.user_id)
    full_name = (await db.execute(profile_stmt)).scalar_one_or_none()
    if full_name and full_name.strip():
        first_name = full_name.strip().split()[0]
    else:
        user_stmt = select(User.username).where(User.id == session.user_id)
        username = (await db.execute(user_stmt)).scalar_one_or_none()
        if username:
            first_name = username.strip().split()[0]

    # Fetch last point
    pt_stmt = (
        select(TrackPoint)
        .where(TrackPoint.session_id == session.id)
        .order_by(TrackPoint.recorded_at.desc())
        .limit(1)
    )
    last_pt = (await db.execute(pt_stmt)).scalar_one_or_none()

    last_pos = None
    if last_pt:
        last_pos = PublicTrackPosition(
            latitude=last_pt.latitude,
            longitude=last_pt.longitude,
            accuracy_m=last_pt.accuracy_m,
            recorded_at=last_pt.recorded_at,
        )

    return PublicTrackOut(
        first_name=first_name,
        status=session.status,
        last_position=last_pos,
        updated_at=last_pt.recorded_at if last_pt else session.started_at,
        expires_at=session.expires_at,
    )


@router.websocket("/track/ws/{token}")
async def public_track_ws(websocket: WebSocket, token: str):
    await ws_manager.connect(f"track:{token}", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(f"track:{token}", websocket)
