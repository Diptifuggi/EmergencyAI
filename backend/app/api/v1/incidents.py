from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from datetime import datetime, timedelta

router = APIRouter(tags=["incidents"])


def _get_current_user():
    """Auth dependency placeholder."""
    return None


def _sample_incident(i):
    now = datetime.utcnow()
    priorities = ['Critical', 'Very High', 'High', 'Moderate', 'Low']
    p = priorities[i % len(priorities)]
    return {
        'id': str(1000 + i),
        'title': f'Sample Incident {i+1}',
        'category': 'Road Accident' if i % 2 == 0 else 'Medical Emergency',
        'call_count': (i + 1) * 3,
        'updated_at': (now - timedelta(minutes=i * 10)).isoformat(),
        'latitude': 20.5 + (i * 0.1),
        'longitude': 78.9 + (i * 0.1),
        'priority': p,
        'severity_score': 80 - i,
        'created_at': now.isoformat(),
        'dispatches': [],
        'timeline': [],
    }


@router.get("/")
async def list_incidents(current_user=Depends(_get_current_user)):
    """Return a sample list of incidents for development."""
    return [_sample_incident(i) for i in range(8)]


@router.get("/{incident_id}")
async def get_incident(incident_id: str, current_user=Depends(_get_current_user)):
    idx = int(incident_id) % 8 if incident_id.isdigit() else 0
    inc = _sample_incident(idx)
    inc['id'] = incident_id
    inc['calls'] = []
    inc['dispatches'] = [
        { 'id': 'd1', 'department': 'Police', 'officer': 'Officer A', 'dispatched_at': datetime.utcnow().isoformat() }
    ]
    inc['timeline'] = [
        {'title': 'First Call Received', 'time': (datetime.utcnow() - timedelta(hours=2)).isoformat()},
        {'title': 'Calls Correlated', 'time': (datetime.utcnow() - timedelta(hours=1, minutes=30)).isoformat()},
        {'title': 'Incident Created', 'time': (datetime.utcnow() - timedelta(hours=1)).isoformat()},
    ]
    return inc


@router.get("/{incident_id}/calls")
async def incident_calls(incident_id: str, current_user=Depends(_get_current_user)):
    """Return related calls for an incident (sample data)."""
    now = datetime.utcnow()
    calls = []
    for i in range(6):
        calls.append({
            'id': f'c{100+i}',
            'caller_name': f'Caller {i+1}',
            'received_at': (now - timedelta(minutes=15*i)).isoformat(),
            'similarity': 0.8 + (i % 3) * 0.05,
            'priority': ['Critical','Very High','High','Moderate','Low'][i%5],
            'transcript': 'Sample transcript text for call ' + str(i+1),
        })
    return calls


@router.post("/{incident_id}/dispatch", status_code=status.HTTP_200_OK)
async def create_dispatch(incident_id: str, payload: dict, current_user=Depends(_get_current_user)):
    """Accept a dispatch for an incident (development stub)."""
    return { 'status': 'ok', 'incident_id': incident_id, 'dispatch': payload }
