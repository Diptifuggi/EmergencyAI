from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import Any
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.emergency_call import EmergencyCall

router = APIRouter()

_LEVEL_LABELS = {
    "critical": "Critical",
    "high": "High",
    "medium": "Moderate",
    "moderate": "Moderate",
    "low": "Low",
}

_TYPE_LABELS = {
    "crime_police": "Crime / Police",
    "medical": "Medical Emergency",
    "police": "Police",
    "fire": "Fire",
    "accident": "Road Accident",
    "women_safety": "Women Safety",
    "domestic_violence": "Domestic Violence",
    "child_safety": "Child Safety",
    "cybercrime": "Cybercrime",
    "lpg": "LPG Leak",
    "robbery": "Robbery",
    "assault": "Assault",
    "harassment": "Harassment",
    "disaster": "Natural Disaster",
    "other": "Other",
    "unknown": "Other",
}


def _get_analysis(call: EmergencyCall) -> dict[str, Any]:
    meta = call.client_metadata or {}
    if not isinstance(meta, dict):
        return {}
    res = meta.get("emergency_analysis")
    if not isinstance(res, dict):
        return {}
    analysis = res.get("analysis")
    return analysis if isinstance(analysis, dict) else {}


def _get_level(call: EmergencyCall, analysis: dict[str, Any]) -> str:
    raw = analysis.get("priority_level") or call.priority
    normalized = str(raw or "").strip().lower()
    return _LEVEL_LABELS.get(normalized, "Low")


def _get_category(call: EmergencyCall, analysis: dict[str, Any]) -> str:
    raw = analysis.get("emergency_type")
    if not raw:
        return "Other"
    key = str(raw).strip().lower()
    return _TYPE_LABELS.get(key, key.replace("_", " ").title())


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(EmergencyCall).order_by(EmergencyCall.created_at.desc()))
    records = result.scalars().all()

    now = datetime.now(UTC)
    today = now.date()

    # 14-day call rate
    days_14 = [today - timedelta(days=i) for i in reversed(range(14))]
    labels_14 = [d.strftime("%b %d") for d in days_14]
    daily_counter: Counter[date] = Counter()

    category_counter: Counter[str] = Counter()
    call_type_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter({"Critical": 0, "High": 0, "Moderate": 0, "Low": 0})
    scores: list[float] = []
    recent_critical: list[dict[str, Any]] = []

    for call in records:
        analysis = _get_analysis(call)
        level = _get_level(call, analysis)
        category = _get_category(call, analysis)

        severity_counter[level] += 1
        category_counter[category] += 1
        call_type_counter[str(call.call_type or "text").lower()] += 1

        call_status = str(call.status or "received").strip()
        status_key = call_status.replace("_", " ").title()
        status_counter[status_key] += 1

        score = analysis.get("priority_score")
        if isinstance(score, (int, float)):
            scores.append(float(score))

        created_at = call.created_at
        if created_at is not None:
            created_day = (
                created_at.astimezone(UTC).date()
                if created_at.tzinfo
                else created_at.date()
            )
            daily_counter[created_day] += 1

        if level in ("Critical", "High") and len(recent_critical) < 5:
            meta = call.client_metadata or {}
            caller_name = meta.get("caller_name") if isinstance(meta, dict) else None
            caller_phone = meta.get("caller_phone") if isinstance(meta, dict) else None
            recent_critical.append({
                "id": str(call.id),
                "caller_name": caller_name or "Anonymous",
                "phone": caller_phone or "Not available",
                "time": created_at.isoformat() if created_at else now.isoformat(),
                "category": category,
                "priority": level,
                "score": int(score) if isinstance(score, (int, float)) else 75,
                "status": status_key,
            })

    total_calls = len(records)
    critical_calls = severity_counter["Critical"]
    todays_calls = daily_counter[today]
    avg_score = (sum(scores) / len(scores)) if scores else 0.0
    # Frontend divides average_severity by 100 if > 100, or displays directly
    average_severity = round(avg_score * 100) if avg_score <= 100 else round(avg_score)

    active_incidents = sum(
        count for st, count in status_counter.items()
        if st.lower() not in ("resolved", "closed")
    )

    top5_cats = [{"name": c} for c, _ in category_counter.most_common(5)]
    if not top5_cats:
        top5_cats = [{"name": "Road Accident"}, {"name": "Medical Emergency"}, {"name": "Fire"}]

    return {
        "updated_at": now.isoformat(),
        "total_calls": total_calls,
        "total_calls_delta": 0.0,
        "critical_calls": critical_calls,
        "critical_calls_delta": 0.0,
        "todays_calls": todays_calls,
        "todays_calls_delta": 0.0,
        "calls_by_status": dict(status_counter),
        "active_incidents": active_incidents,
        "active_incidents_delta": 0.0,
        "average_severity": average_severity,
        "average_severity_delta": 0.0,
        "call_rate": {
            "labels": labels_14,
            "values": [daily_counter[d] for d in days_14],
        },
        "event_status": dict(status_counter),
        "calls_by_category_top5": top5_cats,
        "state_breakdown": [
            {"state": "National / Region", "counts": dict(category_counter.most_common(5))}
        ],
        "severity_distribution": dict(severity_counter),
        "recent_critical_calls": recent_critical,
        "call_type_ratio": dict(call_type_counter),
    }
