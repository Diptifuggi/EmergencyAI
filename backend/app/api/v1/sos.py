from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.dependencies import get_current_citizen, get_current_operator, get_current_user
from ...core.encryption import decrypt_field, decrypt_json, encrypt_json
from ...core.rate_limit import sos_rate_limiter
from ...core.ws_manager import ws_manager
from .audit import record_audit_log
from ...models.emergency_contact import EmergencyContact
from ...models.sos_alert import (
    SOSAlert,
    SOSAlertType,
    SOSEvent,
    SOSLocationStatus,
    SOSLocationUpdate,
    SOSProfileAccessLog,
    SOSStatus,
)
from ...models.track_session import TrackSession, TrackSessionStatus
from ...models.user import User
from ...models.user_notification import UserNotification
from ...models.user_profile import UserProfile
from ...schemas.sos import (
    SOSActionRequest,
    SOSCancelRequest,
    SOSCreateRequest,
    SOSCreateResponse,
    SOSDetailOut,
    SOSListItemOut,
    SOSListResponse,
    SOSLocationUpdateRequest,
    SOSMineDetailOut,
    SOSMineItemOut,
    SOSMineListResponse,
    SOSStatsResponse,
    SOSStatusResponse,
)
from ...schemas.v1 import UserOut
from ...services.emergency_service_directory import SERVICE_DIRECTORY

logger = logging.getLogger(__name__)

router = APIRouter()

_CATEGORY_TO_DIRECTORY_KEY = {
    "police": "police",
    "fire": "fire_service",
    "medical": "ambulance",
    "disaster": "disaster",
    "women": "women_safety_support",
    "child": "child_protection",
    "elderly": "senior_citizen",
    "railway": "railway",
    "general": "integrated_emergency",
}


def get_suggested_numbers(service_category: Optional[str]) -> list[str]:
    cat = (service_category or "general").lower()
    if cat == "woman":
        cat = "women"
    key = _CATEGORY_TO_DIRECTORY_KEY.get(cat, "integrated_emergency")
    return list(SERVICE_DIRECTORY.get(key, ["112"]))


def _add_user_notification(
    db: AsyncSession,
    alert: SOSAlert,
    notification_type: str,
    title: str,
    message: str,
) -> None:
    uid = getattr(alert, "user_id", None)
    if not uid:
        return
    db.add(
        UserNotification(
            user_id=uid,
            alert_id=alert.id,
            notification_type=notification_type,
            title=title,
            message=message,
        )
    )


@router.post("", response_model=SOSCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_sos(
    payload: SOSCreateRequest,
    response: Response,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> SOSCreateResponse:
    # 1. Rate limiting per user
    sos_rate_limiter.check_rate_limit(f"create_{current_user.id}", max_requests=5, window_seconds=30.0)

    now = datetime.now(timezone.utc)

    # 2. Idempotency check: same idempotency_key returns identical alert with 200
    idempotent_stmt = select(SOSAlert).where(SOSAlert.idempotency_key == payload.idempotency_key)
    existing_idemp = (await db.execute(idempotent_stmt)).scalar_one_or_none()
    if existing_idemp:
        logger.debug(f"Idempotent SOS alert hit for alert_id={existing_idemp.id}")
        response.status_code = status.HTTP_200_OK
        return SOSCreateResponse(
            id=existing_idemp.id,
            status=existing_idemp.status,
            received_at=existing_idemp.received_at,
        )

    # 3. 30-second deduplication: active alert (pending/acknowledged) within 30 seconds
    thirty_seconds_ago = now - timedelta(seconds=30)
    dedup_stmt = select(SOSAlert).where(
        SOSAlert.user_id == current_user.id,
        SOSAlert.status.in_([SOSStatus.PENDING.value, SOSStatus.ACKNOWLEDGED.value]),
        SOSAlert.received_at >= thirty_seconds_ago,
    ).order_by(SOSAlert.received_at.desc())
    recent_active = (await db.execute(dedup_stmt)).scalars().first()
    if recent_active:
        logger.debug(f"30s dedup matched existing active alert_id={recent_active.id}")
        response.status_code = status.HTTP_200_OK
        return SOSCreateResponse(
            id=recent_active.id,
            status=recent_active.status,
            received_at=recent_active.received_at,
        )

    # 4. Load user profile snapshot and encrypt it
    profile_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    profile = (await db.execute(profile_stmt)).scalar_one_or_none()

    snapshot_data = {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": getattr(profile, "full_name", None),
        "phone": getattr(profile, "phone", None),
        "alternate_phone": getattr(profile, "alternate_phone", None),
        "guardian_phone": getattr(profile, "guardian_phone", None),
        "guardian_relation": getattr(profile, "guardian_relation", None),
        "address": getattr(profile, "address", None),
        "age": getattr(profile, "age", None),
        "blood_group": getattr(profile, "blood_group", "unknown") or "unknown",
        "allergies": decrypt_field(getattr(profile, "allergies", None)) if getattr(profile, "allergies", None) else None,
        "medical_history": decrypt_field(getattr(profile, "medical_history", None)) if getattr(profile, "medical_history", None) else None,
        "medical_consent": getattr(profile, "medical_consent", False),
        "profile_completed": getattr(profile, "profile_completed", False),
    }
    encrypted_snapshot = encrypt_json(snapshot_data)

    # 5. Create SOSAlert
    alert = SOSAlert(
        id=payload.id,
        idempotency_key=payload.idempotency_key,
        user_id=current_user.id,
        alert_type=payload.alert_type,
        service_category=payload.service_category or "general",
        category_source=payload.category_source or "user_selected",
        status=SOSStatus.PENDING.value,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
        location_status=payload.location_status,
        triggered_at=payload.triggered_at,
        received_at=now,
        battery_pct=payload.battery_pct,
        network_type=payload.network_type,
        device_id=payload.device_id,
        app_version=payload.app_version,
        profile_snapshot_encrypted=encrypted_snapshot,
    )
    db.add(alert)

    # If coordinates provided, store initial location update
    if payload.latitude is not None and payload.longitude is not None:
        loc_update = SOSLocationUpdate(
            alert_id=alert.id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_m,
            recorded_at=now,
        )
        db.add(loc_update)

    # Record initial creation event
    creation_event = SOSEvent(
        alert_id=alert.id,
        actor_type="user",
        actor_id=current_user.id,
        event_type="sos_created",
        payload={
            "alert_type": payload.alert_type,
            "service_category": alert.service_category,
            "location_status": payload.location_status,
        },
        created_at=now,
    )
    db.add(creation_event)

    await db.commit()
    await db.refresh(alert)

    await ws_manager.broadcast(
        "operator",
        {
            "event": "sos.created",
            "alert_id": str(alert.id),
            "alert_type": alert.alert_type,
            "service_category": alert.service_category,
            "status": alert.status,
            "received_at": alert.received_at.isoformat() if alert.received_at else None,
        },
    )

    logger.info(f"SOS alert created id={alert.id} alert_type={alert.alert_type}")
    return SOSCreateResponse(
        id=alert.id,
        status=alert.status,
        received_at=alert.received_at,
    )


@router.post("/{alert_id}/location")
async def update_sos_location(
    alert_id: UUID,
    payload: SOSLocationUpdateRequest,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
):
    sos_rate_limiter.check_min_interval(f"loc_{alert_id}", min_interval_seconds=3.0)

    alert = await db.get(SOSAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    if alert.status in [SOSStatus.CLOSED.value, SOSStatus.CANCELLED.value, SOSStatus.FALSE_ALARM.value]:
        raise HTTPException(status_code=400, detail="Cannot update location for a closed or cancelled alert")

    now = datetime.now(timezone.utc)
    recorded_at = payload.recorded_at or now

    loc_update = SOSLocationUpdate(
        alert_id=alert.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
        recorded_at=recorded_at,
    )
    db.add(loc_update)

    alert.latitude = payload.latitude
    alert.longitude = payload.longitude
    alert.accuracy_m = payload.accuracy_m
    alert.location_status = SOSLocationStatus.AVAILABLE.value
    alert.updated_at = now

    await db.commit()
    return {"success": True, "alert_id": str(alert.id)}


@router.post("/{alert_id}/cancel")
async def cancel_sos(
    alert_id: UUID,
    payload: SOSCancelRequest,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
):
    alert = await db.get(SOSAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    now = datetime.now(timezone.utc)
    alert.status = SOSStatus.CANCELLED.value
    alert.cancelled_at = now
    alert.cancel_reason = payload.reason or "User cancelled"
    alert.updated_at = now

    event = SOSEvent(
        alert_id=alert.id,
        actor_type="user",
        actor_id=current_user.id,
        event_type="sos_cancelled",
        payload={"reason": alert.cancel_reason},
        created_at=now,
    )
    db.add(event)
    alert_type_label = (getattr(alert, "alert_type", None) or "sos").replace("_", " ")
    _add_user_notification(
        db,
        alert,
        "alert_cancelled",
        "SOS Alert Cancelled",
        f"Your {alert_type_label} alert has been cancelled.",
    )

    await db.commit()
    await ws_manager.broadcast(
        "operator",
        {"event": "sos.cancelled", "alert_id": str(alert.id), "status": alert.status},
    )
    return {"id": str(alert.id), "status": alert.status, "cancelled_at": alert.cancelled_at}


@router.get("/mine", response_model=SOSMineListResponse)
async def list_my_sos_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> SOSMineListResponse:
    query = select(SOSAlert).where(SOSAlert.user_id == current_user.id)
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    query = (
        query.order_by(SOSAlert.received_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    alerts = (await db.execute(query)).scalars().all()

    items = [
        SOSMineItemOut(
            id=a.id,
            alert_type=a.alert_type,
            service_category=getattr(a, "service_category", None) or "general",
            status=a.status,
            location_status=a.location_status,
            accuracy_m=a.accuracy_m,
            triggered_at=a.triggered_at,
            received_at=a.received_at,
            acknowledged_at=a.acknowledged_at,
            verified_at=a.verified_at,
            closed_at=a.closed_at,
            cancelled_at=a.cancelled_at,
        )
        for a in alerts
    ]
    return SOSMineListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/mine/{alert_id}", response_model=SOSMineDetailOut)
async def get_my_sos_detail(
    alert_id: UUID,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> SOSMineDetailOut:
    alert = await db.get(SOSAlert, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    event_stmt = (
        select(SOSEvent)
        .where(
            SOSEvent.alert_id == alert.id,
            SOSEvent.event_type != "profile_accessed",
        )
        .order_by(SOSEvent.created_at.asc())
    )
    event_rows = (await db.execute(event_stmt)).scalars().all()
    events = [
        {
            "id": str(e.id),
            "actor_type": e.actor_type,
            "event_type": e.event_type,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in event_rows
    ]

    return SOSMineDetailOut(
        id=alert.id,
        alert_type=alert.alert_type,
        service_category=getattr(alert, "service_category", None) or "general",
        status=alert.status,
        location_status=alert.location_status,
        accuracy_m=alert.accuracy_m,
        triggered_at=alert.triggered_at,
        received_at=alert.received_at,
        acknowledged_at=alert.acknowledged_at,
        verified_at=alert.verified_at,
        closed_at=alert.closed_at,
        cancelled_at=alert.cancelled_at,
        cancel_reason=alert.cancel_reason,
        events=events,
    )


@router.get("/stats", response_model=SOSStatsResponse)
async def get_sos_stats(
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
) -> SOSStatsResponse:
    # Active SOS: pending, acknowledged, verified
    active_q = select(func.count(SOSAlert.id)).where(
        SOSAlert.status.in_([SOSStatus.PENDING.value, SOSStatus.ACKNOWLEDGED.value, SOSStatus.VERIFIED.value])
    )
    active_count = (await db.execute(active_q)).scalar() or 0

    silent_q = select(func.count(SOSAlert.id)).where(
        SOSAlert.alert_type == SOSAlertType.SILENT_SOS.value,
        SOSAlert.status.in_([SOSStatus.PENDING.value, SOSStatus.ACKNOWLEDGED.value, SOSStatus.VERIFIED.value]),
    )
    silent_count = (await db.execute(silent_q)).scalar() or 0

    panic_q = select(func.count(SOSAlert.id)).where(
        SOSAlert.alert_type == SOSAlertType.PANIC_BUTTON.value,
        SOSAlert.status.in_([SOSStatus.PENDING.value, SOSStatus.ACKNOWLEDGED.value, SOSStatus.VERIFIED.value]),
    )
    panic_count = (await db.execute(panic_q)).scalar() or 0

    pending_ver_q = select(func.count(SOSAlert.id)).where(
        SOSAlert.status.in_([SOSStatus.PENDING.value, SOSStatus.ACKNOWLEDGED.value]),
    )
    pending_ver_count = (await db.execute(pending_ver_q)).scalar() or 0

    now = datetime.now(timezone.utc)
    trackme_q = select(func.count(TrackSession.id)).where(
        TrackSession.status == TrackSessionStatus.ACTIVE.value,
        TrackSession.expires_at > now,
    )
    trackme_active_count = (await db.execute(trackme_q)).scalar() or 0

    ack_alerts_stmt = select(SOSAlert.received_at, SOSAlert.acknowledged_at).where(
        SOSAlert.acknowledged_at.is_not(None)
    )
    ack_rows = (await db.execute(ack_alerts_stmt)).all()
    avg_ack_seconds = None
    if ack_rows:
        diffs = [
            (row.acknowledged_at - row.received_at).total_seconds()
            for row in ack_rows
            if row.acknowledged_at and row.received_at
        ]
        if diffs:
            avg_ack_seconds = sum(diffs) / len(diffs)

    return SOSStatsResponse(
        active_sos=active_count,
        silent_sos=silent_count,
        panic_button=panic_count,
        pending_verification=pending_ver_count,
        trackme_active_now=trackme_active_count,
        avg_time_to_acknowledge_seconds=round(avg_ack_seconds, 1) if avg_ack_seconds is not None else None,
    )


@router.get("/{alert_id}/status", response_model=SOSStatusResponse)
async def get_sos_status(
    alert_id: UUID,
    current_user: UserOut = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> SOSStatusResponse:
    alert = await db.get(SOSAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    return SOSStatusResponse(
        id=alert.id,
        status=alert.status,
        alert_type=alert.alert_type,
        service_category=getattr(alert, "service_category", None) or "general",
        category_source=getattr(alert, "category_source", None) or "user_selected",
        triggered_at=alert.triggered_at,
        received_at=alert.received_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        verified_at=alert.verified_at,
        closed_at=alert.closed_at,
        cancelled_at=alert.cancelled_at,
    )


@router.get("", response_model=SOSListResponse)
async def list_sos_alerts(
    status: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    service_category: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
) -> SOSListResponse:
    query = select(SOSAlert)

    if status:
        query = query.where(SOSAlert.status == status)
    if alert_type:
        query = query.where(SOSAlert.alert_type == alert_type)
    if service_category:
        query = query.where(SOSAlert.service_category == service_category)
    if date_from:
        query = query.where(SOSAlert.received_at >= date_from)
    if date_to:
        query = query.where(SOSAlert.received_at <= date_to)

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    query = query.order_by(SOSAlert.received_at.desc()).offset((page - 1) * page_size).limit(page_size)
    alerts = (await db.execute(query)).scalars().all()

    now = datetime.now(timezone.utc)
    items: list[SOSListItemOut] = []
    for a in alerts:
        # Load user/profile details if available
        user_name = None
        user_phone = None
        if a.profile_snapshot_encrypted:
            try:
                snap = decrypt_json(a.profile_snapshot_encrypted)
                if snap:
                    user_name = snap.get("full_name") or snap.get("username")
                    user_phone = snap.get("phone")
            except Exception:
                pass

        age_sec = int((now - a.received_at).total_seconds()) if a.received_at else 0

        items.append(
            SOSListItemOut(
                id=a.id,
                alert_type=a.alert_type,
                service_category=getattr(a, "service_category", None) or "general",
                category_source=getattr(a, "category_source", None) or "user_selected",
                status=a.status,
                user_id=a.user_id,
                user_name=user_name,
                user_phone=user_phone,
                latitude=a.latitude,
                longitude=a.longitude,
                accuracy_m=a.accuracy_m,
                location_status=a.location_status,
                triggered_at=a.triggered_at,
                received_at=a.received_at,
                acknowledged_at=a.acknowledged_at,
                age_seconds=age_sec,
            )
        )

    return SOSListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{alert_id}", response_model=SOSDetailOut)
async def get_sos_detail(
    alert_id: UUID,
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
) -> SOSDetailOut:
    alert = await db.get(SOSAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    now = datetime.now(timezone.utc)

    # AUDIT LOG: Log operator access to medical and profile details
    access_log = SOSProfileAccessLog(
        alert_id=alert.id,
        operator_id=current_user.id,
        accessed_at=now,
    )
    db.add(access_log)

    event = SOSEvent(
        alert_id=alert.id,
        actor_type="operator",
        actor_id=current_user.id,
        event_type="profile_accessed",
        payload={"operator_id": str(current_user.id), "username": current_user.username},
        created_at=now,
    )
    db.add(event)
    await db.commit()

    # Decrypt profile snapshot
    profile_snapshot = None
    if alert.profile_snapshot_encrypted:
        try:
            profile_snapshot = decrypt_json(alert.profile_snapshot_encrypted)
        except Exception as exc:
            logger.warning(f"Failed to decrypt profile snapshot for alert {alert.id}: {exc}")

    # Fetch location history
    loc_stmt = (
        select(SOSLocationUpdate)
        .where(SOSLocationUpdate.alert_id == alert.id)
        .order_by(SOSLocationUpdate.recorded_at.desc())
    )
    loc_rows = (await db.execute(loc_stmt)).scalars().all()
    location_updates = [
        {
            "id": str(l.id),
            "latitude": l.latitude,
            "longitude": l.longitude,
            "accuracy_m": l.accuracy_m,
            "recorded_at": l.recorded_at.isoformat() if l.recorded_at else None,
        }
        for l in loc_rows
    ]

    # Fetch timeline events
    event_stmt = (
        select(SOSEvent)
        .where(SOSEvent.alert_id == alert.id)
        .order_by(SOSEvent.created_at.asc())
    )
    event_rows = (await db.execute(event_stmt)).scalars().all()
    events = [
        {
            "id": str(e.id),
            "actor_type": e.actor_type,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "event_type": e.event_type,
            "payload": e.payload,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in event_rows
    ]

    # Fetch user's emergency contacts if user_id is set
    emergency_contacts_out = []
    if alert.user_id:
        ec_stmt = (
            select(EmergencyContact)
            .where(EmergencyContact.user_id == alert.user_id)
            .order_by(EmergencyContact.is_primary.desc(), EmergencyContact.created_at.asc())
        )
        ec_rows = (await db.execute(ec_stmt)).scalars().all()
        emergency_contacts_out = [
            {
                "id": str(c.id),
                "name": c.name,
                "phone": c.phone,
                "relation": c.relation,
                "notify_on_sos": c.notify_on_sos,
                "is_primary": c.is_primary,
            }
            for c in ec_rows
        ]

    cat = getattr(alert, "service_category", None) or "general"

    return SOSDetailOut(
        id=alert.id,
        idempotency_key=alert.idempotency_key,
        user_id=alert.user_id,
        alert_type=alert.alert_type,
        service_category=cat,
        category_source=getattr(alert, "category_source", None) or "user_selected",
        suggested_numbers=get_suggested_numbers(cat),
        status=alert.status,
        latitude=alert.latitude,
        longitude=alert.longitude,
        accuracy_m=alert.accuracy_m,
        location_status=alert.location_status,
        triggered_at=alert.triggered_at,
        received_at=alert.received_at,
        battery_pct=alert.battery_pct,
        network_type=alert.network_type,
        device_id=alert.device_id,
        app_version=alert.app_version,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        verified_at=alert.verified_at,
        closed_at=alert.closed_at,
        cancelled_at=alert.cancelled_at,
        cancel_reason=alert.cancel_reason,
        close_reason=alert.close_reason,
        profile_snapshot=profile_snapshot,
        emergency_contacts=emergency_contacts_out,
        location_updates=location_updates,
        events=events,
    )


@router.post("/{alert_id}/ack")
async def acknowledge_sos(
    alert_id: UUID,
    payload: SOSActionRequest,
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    alert = await db.get(SOSAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    if alert.status != SOSStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot acknowledge alert in '{alert.status}' status (must be pending)",
        )

    now = datetime.now(timezone.utc)
    alert.status = SOSStatus.ACKNOWLEDGED.value
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = now
    alert.updated_at = now

    event = SOSEvent(
        alert_id=alert.id,
        actor_type="operator",
        actor_id=current_user.id,
        event_type="sos_acknowledged",
        payload={"note": payload.note},
        created_at=now,
    )
    db.add(event)
    record_audit_log(db, current_user, "sos_acknowledged", "sos_alert", str(alert.id), {"note": payload.note})
    _add_user_notification(
        db,
        alert,
        "alert_acknowledged",
        "SOS Alert Acknowledged",
        "An EmergencyIQ operator has acknowledged your SOS alert.",
    )

    await db.commit()
    await ws_manager.broadcast(
        "operator",
        {"event": "sos.updated", "alert_id": str(alert.id), "status": alert.status},
    )
    return {"id": str(alert.id), "status": alert.status, "acknowledged_at": alert.acknowledged_at}


@router.post("/{alert_id}/verify")
async def verify_sos(
    alert_id: UUID,
    payload: SOSActionRequest,
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    alert = await db.get(SOSAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    if alert.status not in [SOSStatus.PENDING.value, SOSStatus.ACKNOWLEDGED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot verify alert in '{alert.status}' status (must be pending or acknowledged)",
        )

    now = datetime.now(timezone.utc)
    alert.status = SOSStatus.VERIFIED.value
    alert.verified_at = now
    alert.updated_at = now

    event = SOSEvent(
        alert_id=alert.id,
        actor_type="operator",
        actor_id=current_user.id,
        event_type="sos_verified",
        payload={"note": payload.note},
        created_at=now,
    )
    db.add(event)
    record_audit_log(db, current_user, "sos_verified", "sos_alert", str(alert.id), {"note": payload.note})
    _add_user_notification(
        db,
        alert,
        "alert_verified",
        "SOS Alert Verified",
        "Your SOS alert has been verified by an EmergencyIQ operator.",
    )

    await db.commit()
    await ws_manager.broadcast(
        "operator",
        {"event": "sos.updated", "alert_id": str(alert.id), "status": alert.status},
    )
    return {"id": str(alert.id), "status": alert.status, "verified_at": alert.verified_at}


@router.post("/{alert_id}/close")
async def close_sos(
    alert_id: UUID,
    payload: SOSActionRequest,
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    alert = await db.get(SOSAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    if alert.status in [SOSStatus.CLOSED.value, SOSStatus.CANCELLED.value, SOSStatus.FALSE_ALARM.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close alert that is already in '{alert.status}' status",
        )

    now = datetime.now(timezone.utc)
    alert.status = SOSStatus.CLOSED.value
    alert.closed_at = now
    alert.close_reason = payload.note or "Closed by operator"
    alert.updated_at = now

    event = SOSEvent(
        alert_id=alert.id,
        actor_type="operator",
        actor_id=current_user.id,
        event_type="sos_closed",
        payload={"note": payload.note},
        created_at=now,
    )
    db.add(event)
    record_audit_log(db, current_user, "sos_closed", "sos_alert", str(alert.id), {"note": payload.note})
    _add_user_notification(
        db,
        alert,
        "alert_closed",
        "SOS Alert Closed",
        "Your SOS alert has been marked as closed.",
    )

    await db.commit()
    await ws_manager.broadcast(
        "operator",
        {"event": "sos.updated", "alert_id": str(alert.id), "status": alert.status},
    )
    return {"id": str(alert.id), "status": alert.status, "closed_at": alert.closed_at}


@router.post("/{alert_id}/false-alarm")
async def false_alarm_sos(
    alert_id: UUID,
    payload: SOSActionRequest,
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    alert = await db.get(SOSAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    if alert.status in [SOSStatus.CLOSED.value, SOSStatus.CANCELLED.value, SOSStatus.FALSE_ALARM.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark alert as false alarm when it is already in '{alert.status}' status",
        )

    now = datetime.now(timezone.utc)
    alert.status = SOSStatus.FALSE_ALARM.value
    alert.closed_at = now
    alert.close_reason = payload.note or "Operator flagged as false alarm"
    alert.updated_at = now

    event = SOSEvent(
        alert_id=alert.id,
        actor_type="operator",
        actor_id=current_user.id,
        event_type="sos_false_alarm",
        payload={"note": payload.note},
        created_at=now,
    )
    db.add(event)
    record_audit_log(db, current_user, "sos_false_alarm", "sos_alert", str(alert.id), {"note": payload.note})
    _add_user_notification(
        db,
        alert,
        "alert_false_alarm",
        "SOS Marked False Alarm",
        "Your SOS alert was closed as a false alarm.",
    )

    await db.commit()
    await ws_manager.broadcast(
        "operator",
        {"event": "sos.updated", "alert_id": str(alert.id), "status": alert.status},
    )
    return {"id": str(alert.id), "status": alert.status, "closed_at": alert.closed_at}
