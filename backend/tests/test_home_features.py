from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_operator, get_current_user
from app.core.rate_limit import sos_rate_limiter
from app.main import app
from app.schemas.v1 import UserOut


def make_user(role_name: str = "User") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        username=f"user_{uuid.uuid4().hex[:6]}",
        email=f"user_{uuid.uuid4().hex[:6]}@example.com",
        role_name=role_name,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def mock_exec_result(scalar_val=None, scalars_list=None, all_rows=None):
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
async def test_sos_service_category_stored_and_returned(client_and_db):
    client, db = client_and_db
    user = make_user("User")
    app.dependency_overrides[get_current_user] = lambda: UserOut.model_validate(user)

    def _refresh(obj):
        if getattr(obj, "received_at", None) is None:
            obj.received_at = datetime.now(timezone.utc)

    db.refresh.side_effect = _refresh
    db.execute.return_value = mock_exec_result(scalar_val=None, scalars_list=[])

    alert_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/sos",
        json={
            "id": alert_id,
            "idempotency_key": f"key-{uuid.uuid4().hex[:8]}",
            "alert_type": "sos",
            "service_category": "fire",
            "category_source": "user_selected",
            "latitude": 23.0225,
            "longitude": 72.5714,
            "location_status": "available",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 201
    added_objs = [call.args[0] for call in db.add.call_args_list]
    sos_obj = next(o for o in added_objs if hasattr(o, "service_category"))
    assert sos_obj.service_category == "fire"
    assert sos_obj.category_source == "user_selected"


@pytest.mark.asyncio
async def test_emergency_contacts_limit_and_indian_phone_validation(client_and_db):
    client, db = client_and_db
    user = make_user("User")
    app.dependency_overrides[get_current_user] = lambda: UserOut.model_validate(user)

    # Invalid phone rejected with 422
    bad_resp = await client.post(
        "/api/v1/users/me/emergency-contacts",
        json={
            "name": "Test Contact",
            "phone": "12345",
            "relation": "Friend",
        },
    )
    assert bad_resp.status_code == 422

    # Max 5 limit enforced with 400
    db.execute.return_value = mock_exec_result(scalar_val=5)
    limit_resp = await client.post(
        "/api/v1/users/me/emergency-contacts",
        json={
            "name": "Sixth Contact",
            "phone": "9876543210",
            "relation": "Friend",
        },
    )
    assert limit_resp.status_code == 400
    assert "Maximum of 5" in limit_resp.json()["detail"]


@pytest.mark.asyncio
async def test_operator_ack_creates_user_notification(client_and_db):
    client, db = client_and_db
    op = make_user("Operator")
    app.dependency_overrides[get_current_operator] = lambda: UserOut.model_validate(op)

    citizen_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    db.get.return_value = SimpleNamespace(
        id=alert_id,
        user_id=citizen_id,
        alert_type="sos",
        service_category="police",
        status="pending",
        acknowledged_by=None,
        acknowledged_at=None,
        updated_at=None,
    )

    resp = await client.post(f"/api/v1/sos/{alert_id}/ack", json={"note": "Dispatching"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"

    added_objs = [call.args[0] for call in db.add.call_args_list]
    notif = next((o for o in added_objs if hasattr(o, "notification_type")), None)
    assert notif is not None
    assert notif.user_id == citizen_id
    assert notif.notification_type == "alert_acknowledged"


@pytest.mark.asyncio
async def test_public_track_endpoint_exposes_no_sensitive_fields_and_handles_expiry(client_and_db):
    client, db = client_and_db
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Active session
    session = SimpleNamespace(
        id=session_id,
        user_id=user_id,
        share_token="tok_secret_abc",
        status="active",
        started_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(minutes=1),  # Already expired!
        ended_at=None,
    )
    last_pt = SimpleNamespace(
        latitude=23.03,
        longitude=72.58,
        accuracy_m=12.0,
        recorded_at=now - timedelta(minutes=2),
    )

    db.execute.side_effect = [
        mock_exec_result(scalar_val=session),
        mock_exec_result(scalar_val="Aarav Sharma"),
        mock_exec_result(scalar_val=last_pt),
    ]

    resp = await client.get("/api/v1/public/track/tok_secret_abc")
    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "Aarav"
    assert body["status"] == "expired"
    assert body["last_position"]["latitude"] == 23.03
    # Ensure no phone, email, address, or medical data exposed
    for forbidden in ("phone", "email", "address", "allergies", "medical_history"):
        assert forbidden not in body


@pytest.mark.asyncio
async def test_non_operator_gets_403_on_operator_sos_list(client_and_db):
    client, _ = client_and_db
    # get_current_operator without override rejects unauthenticated/non-operator
    app.dependency_overrides.pop(get_current_operator, None)
    resp = await client.get("/api/v1/sos")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_reverse_geocode_endpoint(client_and_db):
    client, _ = client_and_db
    user = make_user("User")
    app.dependency_overrides[get_current_user] = lambda: UserOut.model_validate(user)

    with patch("app.api.v1.location.reverse_geocode", new=AsyncMock(return_value="CG Road, Ahmedabad")):
        resp = await client.get("/api/v1/location/reverse?lat=23.0225&lon=72.5714")
        assert resp.status_code == 200
        assert resp.json()["address"] == "CG Road, Ahmedabad"
