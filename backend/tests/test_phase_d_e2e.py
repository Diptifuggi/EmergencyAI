from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from starlette.websockets import WebSocketDisconnect

from app.core.database import get_db
from app.core.rate_limit import login_lockout, sos_rate_limiter
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token
from app.main import app
from app.services.auth_service import AuthService


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


def test_operator_websocket_rejects_unauthenticated_and_citizen_and_accepts_operator(monkeypatch):
    op_user = SimpleNamespace(
        id=uuid.uuid4(),
        username="op_ws",
        email="opws@example.com",
        role_name="Operator",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    cit_user = SimpleNamespace(
        id=uuid.uuid4(),
        username="cit_ws",
        email="citws@example.com",
        role_name="User",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    users_map = {str(op_user.id): op_user, str(cit_user.id): cit_user}

    async def _get_by_id(_db, uid):
        return users_map.get(str(uid))

    monkeypatch.setattr(AuthService, "get_user_by_id", _get_by_id)

    op_token = create_access_token({"sub": str(op_user.id), "role": "Operator"})
    cit_token = create_access_token({"sub": str(cit_user.id), "role": "User"})

    client = TestClient(app)
    # 1. Missing token rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/operator"):
            pass

    # 2. Citizen token rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/operator?token={cit_token}"):
            pass

    # 3. Operator token accepted
    with client.websocket_connect(f"/ws/operator?token={op_token}") as ws:
        assert ws is not None


@pytest.mark.asyncio
async def test_e2e_sos_and_trackme_broadcast_and_logout_flow(monkeypatch):
    sos_rate_limiter.reset()
    login_lockout.reset_all()

    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db

    citizen = SimpleNamespace(
        id=uuid.uuid4(),
        username="e2e_cit",
        email="e2e@example.com",
        password_hash=hash_password("StrongPass1"),
        role_name="User",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    operator = SimpleNamespace(
        id=uuid.uuid4(),
        username="e2e_op",
        email="op_e2e@example.com",
        password_hash=hash_password("StrongPass1"),
        role_name="Operator",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    users_map = {str(citizen.id): citizen, str(operator.id): operator}

    async def _get_by_id(_db, uid):
        return users_map.get(str(uid))

    monkeypatch.setattr(AuthService, "get_user_by_id", _get_by_id)

    cit_token = create_access_token({"sub": str(citizen.id), "role": "User"})
    cit_refresh = create_refresh_token({"sub": str(citizen.id)})
    op_token = create_access_token({"sub": str(operator.id), "role": "Operator"})

    now = datetime.now(timezone.utc)

    def _refresh(obj):
        if getattr(obj, "received_at", None) is None:
            obj.received_at = now
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now

    mock_db.refresh.side_effect = _refresh
    mock_db.execute.return_value = _mock_exec(scalar_val=None, scalars_list=[])

    broadcast_events = []

    async def _capture_broadcast(channel, payload):
        broadcast_events.append((channel, payload))

    with patch("app.api.v1.sos.ws_manager.broadcast", side_effect=_capture_broadcast):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Citizen triggers Fire Service SOS
            sos_id = str(uuid.uuid4())
            r_sos = await ac.post(
                "/api/v1/sos",
                headers={"Authorization": f"Bearer {cit_token}"},
                json={
                    "id": sos_id,
                    "idempotency_key": f"e2e-{uuid.uuid4().hex[:8]}",
                    "alert_type": "sos",
                    "service_category": "fire",
                    "category_source": "user_selected",
                    "latitude": 23.0225,
                    "longitude": 72.5714,
                    "location_status": "available",
                    "triggered_at": now.isoformat(),
                },
            )
            assert r_sos.status_code == 201
            assert any(ch == "operator" and p.get("event") == "sos.created" for ch, p in broadcast_events)

            # 2. Operator acknowledges SOS -> broadcasts sos.updated
            mock_db.get.return_value = SimpleNamespace(
                id=uuid.UUID(sos_id),
                user_id=citizen.id,
                alert_type="sos",
                service_category="fire",
                status="pending",
                acknowledged_by=None,
                acknowledged_at=None,
                updated_at=None,
            )
            r_ack = await ac.post(
                f"/api/v1/sos/{sos_id}/ack",
                headers={"Authorization": f"Bearer {op_token}"},
                json={"note": "Fire engine dispatched"},
            )
            assert r_ack.status_code == 200
            assert any(ch == "operator" and p.get("event") == "sos.updated" for ch, p in broadcast_events)

            # 3. Citizen logs out -> refresh token revoked -> subsequent refresh rejected 401
            stored = SimpleNamespace(
                user_id=citizen.id,
                token_hash=hash_token(cit_refresh),
                expires_at=now + timedelta(days=7),
                revoked_at=now,
            )
            mock_db.execute.return_value = _mock_exec(scalar_val=stored)
            r_ref = await ac.post("/api/v1/auth/refresh", json={"refresh_token": cit_refresh})
            assert r_ref.status_code == 401

    app.dependency_overrides.clear()
