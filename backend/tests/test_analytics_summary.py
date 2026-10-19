from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.analytics import build_analytics_summary


def make_call(*, created_at: datetime, status: str, priority: str, metadata: dict | None = None):
    return SimpleNamespace(
        id=uuid4(),
        created_at=created_at,
        status=status,
        priority=priority,
        client_metadata=metadata or {},
        source="flutter",
        latitude=12.5,
        longitude=77.6,
        location_address=None,
    )


def test_analytics_summary_uses_only_persisted_values_and_marks_missing_aggregates():
    now = datetime(2026, 9, 29, 12, tzinfo=UTC)
    analyzed_call = make_call(
        created_at=now,
        status="analyzed",
        priority="critical",
        metadata={
            "emergency_analysis": {
                "analysis": {
                    "emergency_type": "accident",
                    "priority_level": "CRITICAL",
                    "priority_score": 91,
                }
            }
        },
    )
    unanalyzed_call = make_call(
        created_at=now.replace(hour=10),
        status="received",
        priority="normal",
    )

    summary = build_analytics_summary([analyzed_call, unanalyzed_call], now=now)

    assert summary["total_calls"] == 2
    assert summary["critical_calls"] == 1
    assert summary["pending"] == 1
    assert summary["average_severity"] == 91.0
    assert summary["calls_by_category"] == {"Accident": 1, "Not available": 1}
    assert summary["severity_distribution"] == [
        {"level": "Critical", "count": 1},
        {"level": "High", "count": 0},
        {"level": "Moderate", "count": 0},
        {"level": "Low", "count": 0},
    ]
    assert summary["dispatched"] is None
    assert summary["active_incidents"] is None
    assert summary["todays_calls"] == 2
    assert summary["analytics"]["calls_per_category"]["data"] == [1, 1]
