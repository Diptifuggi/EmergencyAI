from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.rate_limit import login_lockout, sos_rate_limiter
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token
from app.main import app
from app.services.auth_service import AuthService


def _make_user(role_name: str, is_active: bool = True, password: str = "ValidPass1") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        username=f"{role_name.lower()}_{uuid.uuid4().hex[:5]}",
        email=f"{role_name.lower()}_{uuid.uuid4().hex[:5]}@example.com",
        password_hash=hash_password(password),
        role_name=role_name,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
    )


def _mock_exec(scalar_val=None, scalars_list=None):
    res = MagicMock()
    res.scalar.return_value = scalar_val
    res.scalar_one_or_none.return_value = scalar_val
    s_mock = MagicMock()
    s_mock.first.return_value = scalars_list[0] if scalars_list else None
    s_mock.all.return_value = scalars_list or []
    res.scalars.return_value = s_mock
    res.all.return_value = []
    return res


@pytest_asyncio.fixture
async def client_and_db():
    sos_rate_limiter.reset()
    login_lockout.reset_all()
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
async def test_role_endpoint_matrix(client_and_db, monkeypatch):
    client, db = client_and_db
    citizen = _make_user("User")
    operator = _make_user("Operator")
    admin = _make_user("Admin")
    users_map = {str(citizen.id): citizen, str(operator.id): operator, str(admin.id): admin}

    async def _get_by_id(_session, uid):
        return users_map.get(str(uid))

    monkeypatch.setattr(AuthService, "get_user_by_id", _get_by_id)
    db.execute.return_value = _mock_exec(scalar_val=0, scalars_list=[])

    citizen_tok = create_access_token({"sub": str(citizen.id), "role": "User"})
    op_tok = create_access_token({"sub": str(operator.id), "role": "Operator"})
    admin_tok = create_access_token({"sub": str(admin.id), "role": "Admin"})

    # 1. Unauthenticated -> 401
    for path in ["/api/v1/sos", "/api/v1/users/me/profile", "/api/v1/users/", "/api/v1/audit/"]:
        r = await client.get(path)
        assert r.status_code == 401, f"Expected 401 for unauth GET {path}, got {r.status_code}"

    # 2. Citizen token on Operator & Admin endpoints -> 403
    for path in ["/api/v1/sos", "/api/v1/emergency-calls/", "/api/v1/analytics/summary", "/api/v1/dashboard/summary", "/api/v1/users/", "/api/v1/audit/"]:
        r = await client.get(path, headers={"Authorization": f"Bearer {citizen_tok}"})
        assert r.status_code == 403, f"Expected 403 for citizen GET {path}, got {r.status_code}"

    # 3. Operator token on Citizen-only endpoints -> 403
    for path in ["/api/v1/users/me/profile", "/api/v1/users/me/emergency-contacts", "/api/v1/sos/mine"]:
        r = await client.get(path, headers={"Authorization": f"Bearer {op_tok}"})
        assert r.status_code == 403, f"Expected 403 for operator GET {path}, got {r.status_code}"

    # 4. Operator token on Admin-only endpoints -> 403
    for path in ["/api/v1/users/", "/api/v1/audit/", "/api/v1/roles/"]:
        r = await client.get(path, headers={"Authorization": f"Bearer {op_tok}"})
        assert r.status_code == 403, f"Expected 403 for operator GET {path}, got {r.status_code}"

    # 5. Admin token on Admin endpoints -> 200
    for path in ["/api/v1/users/", "/api/v1/audit/", "/api/v1/roles/"]:
        r = await client.get(path, headers={"Authorization": f"Bearer {admin_tok}"})
        assert r.status_code == 200, f"Expected 200 for admin GET {path}, got {r.status_code}"


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_access_token(client_and_db, monkeypatch):
    client, _ = client_and_db
    citizen = _make_user("User")

    async def _get_by_id(_session, uid):
        return citizen if str(uid) == str(citizen.id) else None

    monkeypatch.setattr(AuthService, "get_user_by_id", _get_by_id)
    refresh_tok = create_refresh_token({"sub": str(citizen.id)})

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_tok}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation(client_and_db, monkeypatch):
    client, db = client_and_db
    citizen = _make_user("User")
    raw_refresh = create_refresh_token({"sub": str(citizen.id)})
    stored_row = SimpleNamespace(
        user_id=citizen.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked_at=None,
    )

    async def _get_by_id(_session, uid):
        return citizen if str(uid) == str(citizen.id) else None

    monkeypatch.setattr(AuthService, "get_user_by_id", _get_by_id)
    db.execute.return_value = _mock_exec(scalar_val=stored_row)

    # First refresh succeeds and rotates token
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw_refresh})
    assert r1.status_code == 200
    body = r1.json()
    assert body["access_token"]
    assert body["refresh_token"] != raw_refresh
    assert stored_row.revoked_at is not None

    # Re-using the old revoked refresh token fails with 401
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw_refresh})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_login_lockout_after_5_failures_and_inactive_user(client_and_db, monkeypatch):
    client, _ = client_and_db
    inactive_user = _make_user("User", is_active=False, password="ValidPass1")

    async def _auth_user(_session, email, pwd):
        return None  # AuthService.authenticate_user returns None for inactive or bad pass

    monkeypatch.setattr(AuthService, "authenticate_user", _auth_user)

    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": inactive_user.email, "password": "WrongPassword1"},
        )
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid credentials"

    # 6th attempt triggers 429 lockout
    r_locked = await client.post(
        "/api/v1/auth/login",
        json={"email": inactive_user.email, "password": "ValidPass1"},
    )
    assert r_locked.status_code == 429


@pytest.mark.asyncio
async def test_register_password_policy_and_forced_user_role(client_and_db, monkeypatch):
    client, db = client_and_db

    # Weak password rejected
    r_weak = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "password",  # missing uppercase & digit
        },
    )
    assert r_weak.status_code == 422

    # Strong password forces role_name='User' even if 'Admin' passed
    monkeypatch.setattr(AuthService, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(AuthService, "get_user_by_username", AsyncMock(return_value=None))
    db.execute.return_value = _mock_exec(scalar_val=None)

    created_roles = []

    async def _create_user(_db, username, email, password, role_name="User"):
        created_roles.append(role_name)
        return SimpleNamespace(
            id=uuid.uuid4(),
            username=username,
            email=email,
            role_name=role_name,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(AuthService, "create_user", _create_user)

    r_ok = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "citizen99",
            "email": "citizen99@example.com",
            "password": "StrongPass1",
            "role_name": "Admin",  # Attempt privilege escalation
            "phone": "9876543210",
            "full_name": "Citizen 99",
        },
    )
    assert r_ok.status_code == 201
    assert created_roles == ["User"]
    assert r_ok.json()["role_name"] == "User"
