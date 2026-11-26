from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_operator, get_current_user
from app.core.encryption import decrypt_field, decrypt_json, encrypt_field, encrypt_json
from app.core.rate_limit import sos_rate_limiter
from app.main import app
from app.models.sos_alert import SOSAlert, SOSEvent, SOSLocationUpdate, SOSProfileAccessLog
from app.models.user_profile import UserProfile
from app.schemas.sos import normalize_indian_phone
from app.schemas.v1 import UserOut


def make_user(role="User", **overrides):
    user_id = overrides.get("id", uuid.uuid4())
    values = {
        "id": user_id,
        "username": "citizen_user",
        "email": "citizen@example.com",
        "role_name": role,
        "is_active": True,
        "created_at": datetime.now(UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def mock_exec_result(scalar=None, scalars=None):
    res = MagicMock()
    res.scalar_one_or_none.return_value = scalar
    res.scalar.return_value = scalar
    res.scalars.return_value.first.return_value = (scalars[0] if scalars else scalar)
    res.scalars.return_value.all.return_value = (scalars if scalars is not None else ([scalar] if scalar else []))
    res.all.return_value = scalars or []
    return res


def make_db_execute_mock(idemp=None, dedup=None, profile=None):
    def side_effect(stmt):
        s = str(stmt).lower()
        if "from user_profiles" in s:
            return mock_exec_result(scalar=profile)
        if "where sos_alerts.idempotency_key" in s:
            return mock_exec_result(scalar=idemp)
        if "where sos_alerts.user_id" in s or "sos_alerts.status in" in s:
            return mock_exec_result(scalar=dedup, scalars=[dedup] if dedup else [])
        return mock_exec_result()
    return AsyncMock(side_effect=side_effect)



@pytest_asyncio.fixture
async def client_and_db():
    sos_rate_limiter.reset()
    db = AsyncMock(spec=AsyncSession)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, db

    app.dependency_overrides.clear()
    sos_rate_limiter.reset()


# ==================== Phone & Profile Validation Tests ====================

def test_indian_phone_normalization():
    assert normalize_indian_phone("9876543210") == "+919876543210"
    assert normalize_indian_phone("+919876543210") == "+919876543210"
    assert normalize_indian_phone("919876543210") == "+919876543210"
    assert normalize_indian_phone("09876543210") == "+919876543210"

    with pytest.raises(ValueError):
        normalize_indian_phone("1234567890")  # does not start with 6-9

    with pytest.raises(ValueError):
        normalize_indian_phone("98765")  # too short


def test_encryption_roundtrip():
    secret = "Allergic to penicillin; Asthma diagnosed 2021"
    encrypted = encrypt_field(secret)
    assert encrypted != secret
    assert decrypt_field(encrypted) == secret

    data = {"blood_group": "B+", "allergies": secret}
    enc_json = encrypt_json(data)
    assert decrypt_json(enc_json) == data


# ==================== User Profile Endpoint Tests ====================

@pytest.mark.asyncio
async def test_get_and_update_profile(client_and_db):
    client, db = client_and_db
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=user.role_name,
        is_active=True,
        created_at=user.created_at,
    )

    # 1. Profile not found -> returns default empty profile
    db.execute = AsyncMock(return_value=mock_exec_result(scalar=None))

    get_resp = await client.get("/api/v1/users/me/profile")
    assert get_resp.status_code == 200
    assert get_resp.json()["profile_completed"] is False
    assert get_resp.json()["email"] == user.email

    # 2. Update profile with medical fields without consent -> 422 (validation error)
    bad_put = await client.put(
        "/api/v1/users/me/profile",
        json={
            "full_name": "Test Citizen",
            "phone": "9876543210",
            "allergies": "Peanuts",
            "medical_consent": False,
        },
    )
    assert bad_put.status_code in (400, 422)

    # 3. Update profile with medical fields and consent -> 200
    existing_profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        full_name="Test Citizen",
        phone="+919876543210",
        blood_group="O+",
        allergies=encrypt_field("Peanuts"),
        medical_consent=True,
        profile_completed=True,
        updated_at=datetime.now(UTC),
    )
    db.execute = AsyncMock(return_value=mock_exec_result(scalar=existing_profile))

    good_put = await client.put(
        "/api/v1/users/me/profile",
        json={
            "full_name": "Test Citizen",
            "phone": "9876543210",
            "age": 28,
            "blood_group": "O+",
            "allergies": "Peanuts",
            "medical_consent": True,
        },
    )
    assert good_put.status_code == 200
    data = good_put.json()
    assert data["phone"] == "+919876543210"
    assert data["allergies"] == "Peanuts"
    assert data["profile_completed"] is True
    db.commit.assert_awaited()


# ==================== SOS Creation & Deduplication Tests ====================

@pytest.mark.asyncio
async def test_create_sos_with_location(client_and_db):
    client, db = client_and_db
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=user.role_name,
        is_active=True,
        created_at=user.created_at,
    )

    db.execute = AsyncMock(return_value=mock_exec_result(scalar=None))

    alert_id = uuid.uuid4()
    req_body = {
        "id": str(alert_id),
        "idempotency_key": "idemp-001",
        "alert_type": "sos",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "accuracy_m": 12.5,
        "location_status": "available",
        "triggered_at": datetime.now(UTC).isoformat(),
        "battery_pct": 82,
        "network_type": "wifi",
    }

    resp = await client.post("/api/v1/sos", json=req_body)
    assert resp.status_code in (200, 201)
    assert resp.json()["id"] == str(alert_id)
    assert resp.json()["status"] == "pending"
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_sos_without_location(client_and_db):
    client, db = client_and_db
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=user.role_name,
        is_active=True,
        created_at=user.created_at,
    )

    db.execute = AsyncMock(return_value=mock_exec_result(scalar=None))

    alert_id = uuid.uuid4()
    req_body = {
        "id": str(alert_id),
        "idempotency_key": "idemp-002",
        "alert_type": "silent_sos",
        "latitude": None,
        "longitude": None,
        "location_status": "denied",
        "triggered_at": datetime.now(UTC).isoformat(),
    }

    resp = await client.post("/api/v1/sos", json=req_body)
    assert resp.status_code in (200, 201)
    assert resp.json()["id"] == str(alert_id)
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_sos_idempotency(client_and_db):
    client, db = client_and_db
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=user.role_name,
        is_active=True,
        created_at=user.created_at,
    )

    existing_id = uuid.uuid4()
    existing_alert = SimpleNamespace(
        id=existing_id,
        idempotency_key="idemp-same",
        status="pending",
        received_at=datetime.now(UTC),
    )

    db.execute = AsyncMock(return_value=mock_exec_result(scalar=existing_alert))

    req_body = {
        "id": str(uuid.uuid4()),
        "idempotency_key": "idemp-same",
        "alert_type": "panic_button",
        "location_status": "unavailable",
        "triggered_at": datetime.now(UTC).isoformat(),
    }

    resp = await client.post("/api/v1/sos", json=req_body)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(existing_id)


@pytest.mark.asyncio
async def test_sos_30_second_dedupe(client_and_db):
    client, db = client_and_db
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=user.role_name,
        is_active=True,
        created_at=user.created_at,
    )

    active_id = uuid.uuid4()
    active_alert = SimpleNamespace(
        id=active_id,
        idempotency_key="different-key",
        status="pending",
        received_at=datetime.now(UTC) - timedelta(seconds=10),
    )

    db.execute = make_db_execute_mock(idemp=None, dedup=active_alert, profile=None)

    req_body = {
        "id": str(uuid.uuid4()),
        "idempotency_key": "different-key-2",
        "alert_type": "sos",
        "location_status": "available",
        "triggered_at": datetime.now(UTC).isoformat(),
    }

    resp = await client.post("/api/v1/sos", json=req_body)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(active_id)


# ==================== User Cancel & Live Location ====================

@pytest.mark.asyncio
async def test_cancel_sos(client_and_db):
    client, db = client_and_db
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=user.role_name,
        is_active=True,
        created_at=user.created_at,
    )

    alert_id = uuid.uuid4()
    alert = SimpleNamespace(
        id=alert_id,
        status="pending",
        cancelled_at=None,
        cancel_reason=None,
        updated_at=None,
    )
    db.get.return_value = alert

    resp = await client.post(f"/api/v1/sos/{alert_id}/cancel", json={"reason": "False alarm triggered by accident"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert alert.status == "cancelled"
    assert alert.cancel_reason == "False alarm triggered by accident"


@pytest.mark.asyncio
async def test_update_live_location(client_and_db):
    client, db = client_and_db
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=user.role_name,
        is_active=True,
        created_at=user.created_at,
    )

    alert_id = uuid.uuid4()
    alert = SimpleNamespace(
        id=alert_id,
        status="pending",
        latitude=19.0,
        longitude=72.0,
        accuracy_m=20.0,
        location_status="available",
        updated_at=None,
    )
    db.get.return_value = alert

    resp = await client.post(
        f"/api/v1/sos/{alert_id}/location",
        json={"latitude": 19.0800, "longitude": 72.8800, "accuracy_m": 5.0},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert alert.latitude == 19.0800
    assert alert.longitude == 72.8800


# ==================== Operator Role Checks (403 for Plain Users) ====================

@pytest.mark.asyncio
async def test_operator_endpoints_require_operator_role_403(client_and_db):
    client, db = client_and_db
    citizen = make_user(role="Citizen")
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=citizen.id,
        username=citizen.username,
        email=citizen.email,
        role_name="Citizen",
        is_active=True,
        created_at=citizen.created_at,
    )

    # 1. GET /sos list -> 403
    list_resp = await client.get("/api/v1/sos")
    assert list_resp.status_code == 403
    assert "Operator access required" in list_resp.json()["detail"]

    # 2. GET /sos/stats -> 403
    stats_resp = await client.get("/api/v1/sos/stats")
    assert stats_resp.status_code == 403

    # 3. POST /sos/{id}/ack -> 403
    fake_id = uuid.uuid4()
    ack_resp = await client.post(f"/api/v1/sos/{fake_id}/ack", json={"note": "Ack"})
    assert ack_resp.status_code == 403


# ==================== Operator Status Transitions & Access Log ====================

@pytest.mark.asyncio
async def test_operator_status_transitions_and_access_log(client_and_db):
    client, db = client_and_db
    operator = make_user(role="Operator")
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=operator.id,
        username=operator.username,
        email=operator.email,
        role_name="Operator",
        is_active=True,
        created_at=operator.created_at,
    )

    alert_id = uuid.uuid4()
    profile_data = {
        "full_name": "Emergency Victim",
        "phone": "+919876543210",
        "allergies": "Sulfa drugs",
    }
    alert = SimpleNamespace(
        id=alert_id,
        idempotency_key="idemp-detail",
        user_id=uuid.uuid4(),
        alert_type="sos",
        status="pending",
        latitude=19.0,
        longitude=72.0,
        accuracy_m=10.0,
        location_status="available",
        triggered_at=datetime.now(UTC),
        received_at=datetime.now(UTC),
        battery_pct=50,
        network_type="4G",
        device_id="dev-1",
        app_version="1.0",
        acknowledged_by=None,
        acknowledged_at=None,
        verified_at=None,
        closed_at=None,
        cancelled_at=None,
        cancel_reason=None,
        close_reason=None,
        profile_snapshot_encrypted=encrypt_json(profile_data),
        updated_at=datetime.now(UTC),
    )
    db.get.return_value = alert
    db.execute = AsyncMock(return_value=mock_exec_result(scalars=[]))

    # 1. GET detail -> writes profile access log and decrypts snapshot
    detail_resp = await client.get(f"/api/v1/sos/{alert_id}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert data["profile_snapshot"]["full_name"] == "Emergency Victim"
    assert data["profile_snapshot"]["allergies"] == "Sulfa drugs"
    db.add.assert_called()

    # 2. POST /ack -> pending to acknowledged
    ack_resp = await client.post(f"/api/v1/sos/{alert_id}/ack", json={"note": "Dispatching nearest team"})
    assert ack_resp.status_code == 200
    assert alert.status == "acknowledged"
    assert alert.acknowledged_by == operator.id

    # 3. Invalid transition: cannot ack an already acknowledged alert
    bad_ack = await client.post(f"/api/v1/sos/{alert_id}/ack", json={"note": "Duplicate ack"})
    assert bad_ack.status_code == 400

    # 4. POST /verify -> acknowledged to verified
    verify_resp = await client.post(f"/api/v1/sos/{alert_id}/verify", json={"note": "Confirmed contact"})
    assert verify_resp.status_code == 200
    assert alert.status == "verified"

    # 5. POST /close -> verified to closed
    close_resp = await client.post(f"/api/v1/sos/{alert_id}/close", json={"note": "Resolved safely"})
    assert close_resp.status_code == 200
    assert alert.status == "closed"
    assert alert.close_reason == "Resolved safely"

    # 6. Invalid transition: cannot close already closed alert
    bad_close = await client.post(f"/api/v1/sos/{alert_id}/close", json={"note": "Closing again"})
    assert bad_close.status_code == 400


@pytest.mark.asyncio
async def test_sos_snapshot_unchanged_after_profile_edit(client_and_db):
    """
    Verifies that the encrypted snapshot stored on the SOS record preserves
    the user's profile at alert time and does not mutate when the profile is subsequently edited.
    """
    client, db = client_and_db
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=user.role_name,
        is_active=True,
        created_at=user.created_at,
    )

    initial_profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        full_name="Original Name",
        phone="+919876543210",
        blood_group="A+",
        allergies=encrypt_field("No allergies"),
        medical_consent=True,
        profile_completed=True,
    )

    db.execute = make_db_execute_mock(idemp=None, dedup=None, profile=initial_profile)

    alert_id = uuid.uuid4()
    req_body = {
        "id": str(alert_id),
        "idempotency_key": "idemp-snap-test",
        "alert_type": "sos",
        "location_status": "available",
        "triggered_at": datetime.now(UTC).isoformat(),
    }

    # Captured added objects
    added_objects = []
    db.add.side_effect = lambda obj: added_objects.append(obj)

    resp = await client.post("/api/v1/sos", json=req_body)
    assert resp.status_code == 201

    created_alert = next((obj for obj in added_objects if isinstance(obj, SOSAlert)), None)
    assert created_alert is not None
    assert created_alert.profile_snapshot_encrypted is not None

    snapshot_before = decrypt_json(created_alert.profile_snapshot_encrypted)
    assert snapshot_before["full_name"] == "Original Name"
    assert snapshot_before["phone"] == "+919876543210"

    # User modifies their live profile afterwards
    initial_profile.full_name = "Modified Name"
    initial_profile.phone = "+919999999999"

    # The historical snapshot on the alert remains completely unchanged
    snapshot_after = decrypt_json(created_alert.profile_snapshot_encrypted)
    assert snapshot_after["full_name"] == "Original Name"
    assert snapshot_after["phone"] == "+919876543210"

