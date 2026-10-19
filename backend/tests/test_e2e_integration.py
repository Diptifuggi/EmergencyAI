import io
import uuid
import wave
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.database import engine
from app.main import app


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def valid_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * 800)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_backend_health(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_database_health(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"


@pytest.mark.asyncio
async def test_text_emergency_submission_and_persistence(async_client: AsyncClient):
    payload = {
        "text": "Major car collision at Crossroad 4 near hospital",
        "language": "en",
        "latitude": 23.0225,
        "longitude": 72.5714,
        "location_accuracy": 5.0,
        "location_timestamp": "2026-10-17T12:00:00Z",
        "source": "flutter",
        "priority": "high",
        "client_metadata": {"caller_name": "Rohan Patel", "caller_phone": "+919876543210"},
    }

    with patch("app.api.v1.emergency_calls.reverse_geocode", new_callable=AsyncMock) as mock_geo:
        mock_geo.return_value = "Crossroad 4, Ahmedabad, Gujarat"
        response = await async_client.post("/api/v1/emergency-calls/text", json=payload)

    assert response.status_code == 201, response.text
    created = response.json()
    call_id = created["id"]
    assert call_id is not None
    assert created["latitude"] == 23.0225
    assert created["longitude"] == 72.5714
    assert created["location_status"] == "captured"

    # Verify retrieval via detail API
    get_res = await async_client.get(f"/api/v1/emergency-calls/{call_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["id"] == call_id
    assert detail["text_content"] == payload["text"]

    # Verify in list API
    list_res = await async_client.get("/api/v1/emergency-calls/?limit=10")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(item["id"] == call_id for item in items)

    # Clean up test record from database safely
    async with engine.connect() as conn:
        await conn.execute(text(f"DELETE FROM emergency_calls WHERE id = '{call_id}'"))
        await conn.commit()


@pytest.mark.asyncio
async def test_emergency_without_gps_coordinates(async_client: AsyncClient):
    payload = {
        "text": "Report without GPS location",
        "language": "en",
        "latitude": None,
        "longitude": None,
        "source": "flutter",
    }
    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)
    assert response.status_code == 201
    created = response.json()
    call_id = created["id"]
    assert created["latitude"] is None
    assert created["longitude"] is None
    assert created["location_status"] == "unavailable"

    async with engine.connect() as conn:
        await conn.execute(text(f"DELETE FROM emergency_calls WHERE id = '{call_id}'"))
        await conn.commit()


@pytest.mark.asyncio
async def test_invalid_coordinates_rejected(async_client: AsyncClient):
    payload = {
        "text": "Report with out-of-range latitude",
        "language": "en",
        "latitude": 125.0,  # Invalid: > 90
        "longitude": 72.5,
    }
    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analytics_and_dashboard_summaries(async_client: AsyncClient):
    # Analytics summary
    res1 = await async_client.get("/api/v1/analytics/summary")
    assert res1.status_code == 200
    data1 = res1.json()
    assert "total_calls" in data1
    assert "critical_calls" in data1
    assert "calls_by_status" in data1
    assert "analytics" in data1

    # Dashboard summary
    res2 = await async_client.get("/api/v1/dashboard/summary")
    assert res2.status_code == 200
    data2 = res2.json()
    assert "total_calls" in data2
    assert "calls_by_status" in data2
    assert "call_rate" in data2


@pytest.mark.asyncio
async def test_incidents_api_with_postgresql(async_client: AsyncClient):
    res = await async_client.get("/api/v1/incidents/")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    if len(items) > 0:
        first = items[0]
        assert "id" in first
        assert "title" in first
        assert "status" in first
        # Verify get detail
        detail_res = await async_client.get(f"/api/v1/incidents/{first['id']}")
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == first["id"]


@pytest.mark.asyncio
async def test_calls_api_with_postgresql(async_client: AsyncClient):
    res = await async_client.get("/api/v1/calls/")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    if len(items) > 0:
        first = items[0]
        assert "id" in first
        assert "priority" in first
        assert "status" in first
        # Verify get detail
        detail_res = await async_client.get(f"/api/v1/calls/{first['id']}")
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == first["id"]


@pytest.mark.asyncio
async def test_audio_emergency_submission_and_patch(async_client: AsyncClient):
    from pathlib import Path
    audio_path = Path(__file__).resolve().parents[2] / "Sarvam_STT_Test" / "test_audio.wav"
    assert audio_path.exists(), f"Audio file not found at {audio_path}"
    audio_bytes = audio_path.read_bytes()

    files = {"file": ("test_audio.wav", audio_bytes, "audio/wav")}
    data = {
        "transcription": "Emergency fire in building nearby",
        "language": "en",
        "latitude": "23.0300",
        "longitude": "72.5800",
        "source": "flutter",
        "priority": "critical",
    }
    with patch("app.api.v1.emergency_calls.reverse_geocode", new_callable=AsyncMock) as mock_geo:
        mock_geo.return_value = "Ellisbridge, Ahmedabad, Gujarat"
        response = await async_client.post("/api/v1/emergency-calls/voice-text", files=files, data=data)

    assert response.status_code == 201, response.text
    created = response.json()
    call_id = created["id"]
    assert created["call_type"] == "voice_text"
    assert created["transcription"] == data["transcription"]
    assert created["latitude"] == 23.03
    assert created["audio_url"] is not None

    # Test patch
    patch_res = await async_client.patch(f"/api/v1/emergency-calls/{call_id}", json={"status": "resolved"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "resolved"

    # Cleanup safely
    async with engine.connect() as conn:
        await conn.execute(text(f"DELETE FROM emergency_calls WHERE id = '{call_id}'"))
        await conn.commit()

