from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.v1.incidents import _map_to_incident_out


def _call(metadata: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id="call-1",
        client_metadata=metadata,
        call_type="text",
        location_address=None,
        text_content="Fire reported",
        transcription=None,
        priority="normal",
        status="analyzed",
        latitude=22.5,
        longitude=72.9,
        created_at=datetime.now(timezone.utc),
    )


def test_incident_projection_reads_direct_analysis_and_preserves_zero_score() -> None:
    incident = _map_to_incident_out(
        _call({"emergency_analysis": {"emergency_type": "fire", "priority_score": 0}})
    )

    assert incident.incident_type == "Fire"
    assert incident.severity == 0


def test_incident_projection_does_not_invent_score_when_analysis_is_missing() -> None:
    incident = _map_to_incident_out(_call({}))

    assert incident.severity is None
    assert incident.incident_type == "Not Reported"
