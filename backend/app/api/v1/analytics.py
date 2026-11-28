from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any, Iterable

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.dependencies import get_current_operator
from ...models.emergency_call import EmergencyCall
from ...schemas.v1 import UserOut

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
    "medical": "Medical",
    "police": "Police",
    "fire": "Fire",
    "accident": "Accident",
    "women_safety": "Women Safety",
    "domestic_violence": "Domestic Violence",
    "child_safety": "Child Safety",
    "cybercrime": "Cybercrime",
    "lpg": "LPG",
    "robbery": "Robbery",
    "assault": "Assault",
    "harassment": "Harassment",
    "disaster": "Disaster",
    "other": "Other",
    "unknown": "Unknown",
}


def _analysis(call: EmergencyCall) -> dict[str, Any]:
    metadata = call.client_metadata or {}
    result = metadata.get("emergency_analysis") if isinstance(metadata, dict) else None
    analysis = result.get("analysis") if isinstance(result, dict) else None
    return analysis if isinstance(analysis, dict) else {}


def _level(call: EmergencyCall, analysis: dict[str, Any]) -> str | None:
    raw = analysis.get("priority_level") or call.priority
    return _LEVEL_LABELS.get(str(raw or "").strip().lower())


def _category(call: EmergencyCall, analysis: dict[str, Any]) -> str:
    raw = analysis.get("emergency_type")
    if not raw:
        return "Not available"
    key = str(raw).strip().lower()
    return _TYPE_LABELS.get(key, key.replace("_", " ").title())


def build_analytics_summary(
    calls: Iterable[EmergencyCall], *, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    records = sorted(
        calls,
        key=lambda call: call.created_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    analyses = {str(call.id): _analysis(call) for call in records}
    status_counts = Counter(str(call.status or "unknown").lower() for call in records)
    category_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    daily_counts: Counter[date] = Counter()
    monthly_categories: dict[str, Counter[str]] = defaultdict(Counter)
    scores: list[float] = []

    today = now.date()
    first_day_this_month = today.replace(day=1)
    month_starts = []
    month_start = first_day_this_month
    for _ in range(6):
        month_starts.append(month_start)
        month_start = (month_start - timedelta(days=1)).replace(day=1)
    month_starts.reverse()
    month_labels = [month.strftime("%Y-%m") for month in month_starts]

    for call in records:
        analysis = analyses[str(call.id)]
        category = _category(call, analysis)
        category_counts[category] += 1
        source_counts[str(call.source or "Not available")] += 1
        level = _level(call, analysis)
        if level:
            level_counts[level] += 1
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
            if today - timedelta(days=6) <= created_day <= today:
                daily_counts[created_day] += 1
            month = created_day.strftime("%Y-%m")
            if month in month_labels:
                monthly_categories[month][category] += 1

    days = [today - timedelta(days=offset) for offset in reversed(range(7))]
    day_labels = [day.strftime("%b %d") for day in days]
    severity_levels = ["Critical", "High", "Moderate", "Low"]
    categories = sorted(category_counts)
    monthly_datasets = [
        {
            "label": category,
            "data": [monthly_categories[month][category] for month in month_labels],
        }
        for category in sorted(
            {name for values in monthly_categories.values() for name in values}
        )
    ]

    recent_calls = []
    for call in records[:5]:
        analysis = analyses[str(call.id)]
        metadata = call.client_metadata or {}
        metadata = metadata if isinstance(metadata, dict) else {}
        created_at = call.created_at
        recent_calls.append(
            {
                "id": str(call.id),
                "caller_name": metadata.get("caller_name"),
                "caller_phone": metadata.get("caller_phone"),
                "category": _category(call, analysis),
                "priority_level": _level(call, analysis),
                "final_score": analysis.get("priority_score"),
                "status": call.status,
                "created_at": created_at.isoformat() if created_at else None,
                "latitude": call.latitude,
                "longitude": call.longitude,
                "location_address": call.location_address,
            }
        )

    return {
        "total_calls": len(records),
        "critical_calls": level_counts["Critical"],
        "dispatched": None,
        "resolved": status_counts["resolved"],
        "average_severity": round(sum(scores) / len(scores), 1) if scores else None,
        "todays_calls": daily_counts[today],
        "pending": sum(
            status_counts[value]
            for value in ("received", "pending_transcription", "analyzing", "analysis_failed")
        ),
        "active_incidents": None,
        "calls_by_status": dict(status_counts),
        "calls_by_category": dict(category_counts),
        "call_rate_7days": {"labels": day_labels, "data": [daily_counts[day] for day in days]},
        "severity_distribution": [
            {"level": level, "count": level_counts[level]} for level in severity_levels
        ],
        "recent_calls": recent_calls,
        "channels": [
            {"source": name, "count": count}
            for name, count in source_counts.most_common()
        ],
        "analytics": {
            "calls_per_category": {
                "labels": categories,
                "data": [category_counts[name] for name in categories],
            },
            "daily_trends": {"labels": day_labels, "data": [daily_counts[day] for day in days]},
            "priority_distribution": {
                "labels": severity_levels,
                "data": [level_counts[level] for level in severity_levels],
                "colors": ["#dc2626", "#f97316", "#16a34a", "#3b82f6"],
            },
            "monthly_summary": {"labels": month_labels, "datasets": monthly_datasets},
        },
    }


@router.get("/summary")
async def get_analytics_summary(
    current_user: UserOut = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(EmergencyCall).order_by(EmergencyCall.created_at.desc()))
    return build_analytics_summary(result.scalars().all())
