from fastapi import APIRouter
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/summary")
async def summary():
    # Return sample dashboard summary for frontend development
    now = datetime.utcnow()
    labels = [(now - timedelta(days=i)).strftime('%b %d') for i in range(13, -1, -1)]
    values = [10 + (i % 5) * 3 for i in range(len(labels))]

    event_status = {"Pending": 12, "Processing": 8, "Assigned": 20, "Resolved": 60}

    calls_by_status = {"Pending": 12, "Processing": 8, "Assigned": 20, "Resolved": 60}

    calls_by_category_top5 = [
        {"name": "Road Accident"},
        {"name": "Medical Emergency"},
        {"name": "Fire"},
        {"name": "Women Safety"},
        {"name": "Other"},
    ]

    state_breakdown = [
        {"state": "State A", "counts": {"Road Accident": 5, "Medical Emergency": 8, "Fire": 2, "Women Safety": 1, "Other": 3}},
        {"state": "State B", "counts": {"Road Accident": 3, "Medical Emergency": 4, "Fire": 6, "Women Safety": 2, "Other": 1}},
        {"state": "State C", "counts": {"Road Accident": 7, "Medical Emergency": 2, "Fire": 1, "Women Safety": 5, "Other": 4}},
    ]

    severity_distribution = {"Critical": 5, "Very High": 8, "High": 15, "Moderate": 30, "Low": 42}

    recent_critical_calls = [
        {"id": 1, "caller_name": "John Doe", "phone": "+911234567890", "time": (now - timedelta(minutes=15)).isoformat(), "category": "Road Accident", "priority": "Critical", "score": 85, "status": "Pending"},
        {"id": 2, "caller_name": "Jane Smith", "phone": "+919876543210", "time": (now - timedelta(hours=1)).isoformat(), "category": "Medical Emergency", "priority": "Very High", "score": 78, "status": "Assigned"},
    ]

    return {
        "updated_at": now.isoformat(),
        "total_calls": sum(values),
        "total_calls_delta": 3.4,
        "critical_calls": 5,
        "critical_calls_delta": -1.2,
        "todays_calls": 12,
        "todays_calls_delta": 0.5,
        "calls_by_status": calls_by_status,
        "active_incidents": 7,
        "active_incidents_delta": 1.0,
        "average_severity": 6140,  # represented as integer out of 10000 in some systems; frontend divides by 100
        "average_severity_delta": 0.2,
        "call_rate": {"labels": labels, "values": values},
        "event_status": event_status,
        "calls_by_category_top5": calls_by_category_top5,
        "state_breakdown": state_breakdown,
        "severity_distribution": severity_distribution,
        "recent_critical_calls": recent_critical_calls,
        "call_type_ratio": {"voice": 60, "sms": 30, "other": 10},
    }
