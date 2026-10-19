from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import AuthService
from app.core.database import get_db
from app.main import app


@pytest_asyncio.fixture
async def async_client():
    db = AsyncMock(spec=AsyncSession)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, db
    app.dependency_overrides.pop(get_db, None)


def make_user(**overrides):
    values = {
        "id": uuid4(),
        "username": "dispatcher01",
        "email": "dispatcher@example.com",
        "role_name": "Operator",
        "is_active": True,
        "created_at": datetime.now(UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_register_creates_postgres_user_and_returns_public_user(async_client, monkeypatch):
    client, db = async_client
    user = make_user()
    monkeypatch.setattr(AuthService, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(AuthService, "get_user_by_username", AsyncMock(return_value=None))
    monkeypatch.setattr(AuthService, "create_user", AsyncMock(return_value=user))

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": user.username,
            "email": user.email,
            "password": "secure-test-password",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role_name": user.role_name,
        "is_active": True,
        "created_at": user.created_at.isoformat().replace("+00:00", "Z"),
    }
    assert "password" not in response.json()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(async_client, monkeypatch):
    client, db = async_client
    monkeypatch.setattr(AuthService, "get_user_by_email", AsyncMock(return_value=make_user()))

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "anotherdispatcher",
            "email": "dispatcher@example.com",
            "password": "secure-test-password",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_accepts_a_persisted_user(async_client, monkeypatch):
    client, _ = async_client
    user = make_user()
    monkeypatch.setattr(AuthService, "authenticate_user", AsyncMock(return_value=user))

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "secure-test-password"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]
