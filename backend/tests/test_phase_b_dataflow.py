from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_operator, get_optional_user
from app.core.encryption import encrypt_field
from app.main import app
from app.schemas.v1 import UserOut


def _mock_exec(scalar_val=None, scalars_list=None, all_rows=None):
    res = MagicMock()
    res.scalar.return_value = scalar_val
    res.scalar_one.return_value = scalar_val or 0
    res.scalar_one_or_none.return_value = scalar_val
    s_mock = MagicMock()
    s_mock.first.return_value = scalars_list[0] if scalars_list else None
    s_mock.all.return_value = scalars_list or []
    res.scalars.return_value = s_mock
    res.all.return_value = all_rows or []
    return res


@pytest_asyncio.fixture
async def client_and_db():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.scalar = AsyncMock(return_value=None)

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, mock_db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_text_emergency_attaches_authenticated_user_id(client_and_db):
    client, db = client_and_db
    uid = uuid.uuid4()
    app.dependency_overrides[get_optional_user] = lambda: UserOut(
        id=uid,
        username="citizen_b",
        email="cb@example.com",
        role_name="User",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    now = datetime.now(timezone.utc)

    def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now

    db.refresh.side_effect = _refresh

    with (
        patch("app.api.v1.emergency_calls._schedule_emergency_analysis"),
        patch("app.api.v1.emergency_calls._schedule_location_address"),
    ):
        resp = await client.post(
            "/api/v1/emergency-calls/text",
            json={"text": "Smoke near market", "language": "en"},
        )
    assert resp.status_code == 201
    added = db.add.call_args.args[0]
    assert added.user_id == uid
    assert resp.json()["user_id"] == str(uid)


@pytest.mark.asyncio
async def test_sos_stats_includes_pending_verification_and_trackme_active(client_and_db):
    client, db = client_and_db
    op_id = uuid.uuid4()
    app.dependency_overrides[get_current_operator] = lambda: UserOut(
        id=op_id,
        username="op_b",
        email="opb@example.com",
        role_name="Operator",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.execute.side_effect = [
        _mock_exec(scalar_val=4),   # active_sos
        _mock_exec(scalar_val=1),   # silent_sos
        _mock_exec(scalar_val=2),   # panic_button
        _mock_exec(scalar_val=3),   # pending_verification
        _mock_exec(scalar_val=5),   # trackme_active_now
        _mock_exec(all_rows=[]),    # ack_alerts
    ]

    resp = await client.get("/api/v1/sos/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_sos"] == 4
    assert data["pending_verification"] == 3
    assert data["trackme_active_now"] == 5


@pytest.mark.asyncio
async def test_operator_user_summary_decrypts_consented_medical_and_logs_audit(client_and_db):
    client, db = client_and_db
    op_id = uuid.uuid4()
    target_uid = uuid.uuid4()
    app.dependency_overrides[get_current_operator] = lambda: UserOut(
        id=op_id,
        username="op_b",
        email="opb@example.com",
        role_name="Operator",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.get.return_value = SimpleNamespace(
        id=target_uid,
        username="citizen_target",
        email="target@example.com",
        role_name="User",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    profile = SimpleNamespace(
        full_name="Meera Patel",
        phone="+919876543210",
        alternate_phone=None,
        guardian_phone="+919876543211",
        guardian_relation="Mother",
        address="Navrangpura, Ahmedabad",
        age=26,
        blood_group="B+",
        allergies=encrypt_field("Sulfa drugs"),
        medical_history=encrypt_field("Asthma"),
        medical_consent=True,
        medical_consent_at=datetime.now(timezone.utc),
        profile_completed=True,
    )

    db.execute.side_effect = [
        _mock_exec(scalar_val=profile),
        _mock_exec(scalars_list=[]),  # emergency_contacts
        _mock_exec(scalars_list=[]),  # sos_alerts
        _mock_exec(scalars_list=[]),  # reports
        _mock_exec(scalars_list=[]),  # track_sessions
    ]

    resp = await client.get(f"/api/v1/users/{target_uid}/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"]["full_name"] == "Meera Patel"
    assert body["profile"]["allergies"] == "Sulfa drugs"
    assert body["profile"]["medical_history"] == "Asthma"
    # Verify audit log recorded
    added_objs = [c.args[0] for c in db.add.call_args_list]
    assert any(getattr(o, "action", None) == "user_profile_viewed" for o in added_objs)
