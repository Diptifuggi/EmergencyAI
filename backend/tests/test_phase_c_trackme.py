from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_citizen, get_current_operator
from app.core.rate_limit import sos_rate_limiter
from app.main import app
from app.schemas.v1 import UserOut


def _mock_exec(scalar_val=None, scalars_list=None, all_rows=None):
    res = MagicMock()
    res.scalar.return_value = scalar_val
    res.scalar_one_or_none.return_value = scalar_val
    s_mock = MagicMock()
    s_mock.first.return_value = scalars_list[0] if scalars_list else None
    s_mock.all.return_value = scalars_list or []
    res.scalars.return_value = s_mock
    res.all.return_value = all_rows or []
    return res


@pytest_asyncio.fixture
async def client_and_db():
    sos_rate_limiter.reset()
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, mock_db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trackme_batch_points_dedup_and_rejects_future_timestamp(client_and_db):
    client, db = client_and_db
    uid = uuid.uuid4()
    session_id = uuid.uuid4()
    app.dependency_overrides[get_current_citizen] = lambda: UserOut(
        id=uid,
        username="track_user",
        email="tu@example.com",
        role_name="User",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    now = datetime.now(timezone.utc)
    db.get.return_value = SimpleNamespace(
        id=session_id,
        user_id=uid,
        share_token="tok_123",
        sos_alert_id=None,
        share_with_control_room=False,
        status="active",
        expires_at=now + timedelta(hours=1),
    )

    # 1. Reject point with timestamp 20 minutes in the future
    db.execute.return_value = _mock_exec(all_rows=[])
    future_ts = (now + timedelta(minutes=20)).isoformat()
    bad_resp = await client.post(
        f"/api/v1/track/{session_id}/points",
        json={
            "points": [
                {"client_point_id": "pt-future", "latitude": 23.0, "longitude": 72.5, "recorded_at": future_ts}
            ]
        },
    )
    assert bad_resp.status_code == 422

    # 2. Batch upload deduplicates existing client_point_id
    sos_rate_limiter.reset()
    db.execute.return_value = _mock_exec(all_rows=[("pt-1",)])  # pt-1 already exists

    def _refresh(pt):
        if getattr(pt, "id", None) is None:
            pt.id = uuid.uuid4()
        if getattr(pt, "recorded_at", None) is None:
            pt.recorded_at = now

    db.refresh.side_effect = _refresh

    ok_resp = await client.post(
        f"/api/v1/track/{session_id}/points",
        json={
            "points": [
                {"client_point_id": "pt-1", "latitude": 23.01, "longitude": 72.51},
                {"client_point_id": "pt-2", "latitude": 23.02, "longitude": 72.52},
            ]
        },
    )
    assert ok_resp.status_code == 200
    items = ok_resp.json()
    assert len(items) == 1
    assert items[0]["client_point_id"] == "pt-2"


@pytest.mark.asyncio
async def test_operator_track_access_requires_control_room_share_or_sos_and_logs_audit(client_and_db):
    client, db = client_and_db
    op_id = uuid.uuid4()
    session_id = uuid.uuid4()
    app.dependency_overrides[get_current_operator] = lambda: UserOut(
        id=op_id,
        username="op_track",
        email="opt@example.com",
        role_name="Operator",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    now = datetime.now(timezone.utc)
    # 1. Unshared and no SOS -> 403 Forbidden
    db.get.return_value = SimpleNamespace(
        id=session_id,
        user_id=uuid.uuid4(),
        share_token="tok_priv",
        duration_hours=1,
        share_with_control_room=False,
        sos_alert_id=None,
        status="active",
        started_at=now,
        expires_at=now + timedelta(hours=1),
        ended_at=None,
    )
    r_priv = await client.get(f"/api/v1/track/operator/{session_id}")
    assert r_priv.status_code == 403

    # 2. Shared with control room -> 200 OK + distance + audit log
    db.get.return_value.share_with_control_room = True
    p1 = SimpleNamespace(
        id=uuid.uuid4(),
        client_point_id="p1",
        latitude=23.0225,
        longitude=72.5714,
        accuracy_m=10.0,
        battery_pct=90,
        recorded_at=now - timedelta(seconds=30),
    )
    p2 = SimpleNamespace(
        id=uuid.uuid4(),
        client_point_id="p2",
        latitude=23.0235,
        longitude=72.5724,
        accuracy_m=10.0,
        battery_pct=89,
        recorded_at=now,
    )
    db.execute.return_value = _mock_exec(scalars_list=[p1, p2])

    r_ok = await client.get(f"/api/v1/track/operator/{session_id}")
    assert r_ok.status_code == 200
    body = r_ok.json()
    assert body["distance_meters"] > 100.0
    assert len(body["points"]) == 2
    added_objs = [c.args[0] for c in db.add.call_args_list]
    assert any(getattr(o, "action", None) == "track_session_viewed" for o in added_objs)
