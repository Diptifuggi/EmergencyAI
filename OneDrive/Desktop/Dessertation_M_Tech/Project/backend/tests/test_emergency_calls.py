import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.emergency_analysis import STATUS_ANALYZED, STATUS_PENDING_TRANSCRIPTION


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def emergency_text_payload() -> dict:
    return {
        "text": "There has been a road accident near Anand railway station",
        "language": "en",
        "latitude": 22.5645,
        "longitude": 72.9289,
    }


@pytest.fixture(autouse=True)
def mock_successful_analysis():
    with patch(
        "app.services.emergency_call_analysis_runner.EmergencyAnalysisService.analyze",
        new_callable=AsyncMock,
    ) as mocked:
        from tests.conftest import make_analysis_result

        mocked.return_value = make_analysis_result()
        yield mocked


@pytest.mark.asyncio
async def test_create_text_emergency(async_client: AsyncClient) -> None:
    payload = emergency_text_payload()

    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == STATUS_ANALYZED
    assert data["text_content"] == payload["text"]
    assert data["language"] == payload["language"]
    assert data["call_type"] == "text"
    assert "emergency_analysis" in data["client_metadata"]
    assert uuid.UUID(data["id"])


@pytest.mark.asyncio
async def test_create_audio_emergency(async_client: AsyncClient, tmp_path: Path) -> None:
    temp_path = tmp_path / "test_emergency_audio.m4a"
    temp_path.write_bytes(b"RIFF....\x00\x00\x00")

    with temp_path.open("rb") as file_handle:
        files = {"file": ("test_emergency_audio.m4a", file_handle, "audio/m4a")}
        data = {"language": "en"}
        response = await async_client.post("/api/v1/emergency-calls/audio", files=files, data=data)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == STATUS_PENDING_TRANSCRIPTION
    assert data["call_type"] == "audio"
    assert data["audio_file_path"] is not None
    assert data["original_audio_filename"] == "test_emergency_audio.m4a"
    assert data["audio_url"] is not None


@pytest.mark.asyncio
async def test_create_voice_and_text(async_client: AsyncClient, tmp_path: Path) -> None:
    temp_path = tmp_path / "voice.m4a"
    temp_path.write_bytes(b"fake-audio-bytes")

    with temp_path.open("rb") as file_handle:
        files = {"file": ("voice.m4a", file_handle, "audio/m4a")}
        data = {
            "language": "en",
            "transcription": "Help needed at the highway junction",
            "client_metadata": '{"device":"test"}',
        }
        response = await async_client.post(
            "/api/v1/emergency-calls/voice-text", files=files, data=data
        )

    assert response.status_code == 201
    body = response.json()
    assert body["call_type"] == "voice_text"
    assert body["transcription"] == "Help needed at the highway junction"
    assert body["text_content"] == "Help needed at the highway junction"
    assert body["status"] == STATUS_ANALYZED
    assert body["client_metadata"]["device"] == "test"
    assert "emergency_analysis" in body["client_metadata"]
    assert body["audio_url"] is not None


@pytest.mark.asyncio
async def test_create_audio_emergency_converts_mp4_to_mp3(async_client: AsyncClient, tmp_path: Path) -> None:
    temp_path = tmp_path / "voice.mp4"
    temp_path.write_bytes(b"fake-mp4-audio-bytes")

    with patch(
        "app.api.v1.emergency_calls.convert_uploaded_audio_to_mp3",
        return_value=(b"fake-mp3-bytes", ".mp3", "audio/mpeg"),
    ) as mocked_converter:
        with temp_path.open("rb") as file_handle:
            files = {"file": ("voice.mp4", file_handle, "video/mp4")}
            data = {"language": "en"}
            response = await async_client.post(
                "/api/v1/emergency-calls/audio",
                files=files,
                data=data,
            )

    assert response.status_code == 201
    body = response.json()
    assert body["audio_file_path"].endswith(".mp3")
    assert body["audio_content_type"] == "audio/mpeg"
    assert body["original_audio_filename"] == "voice.mp4"
    mocked_converter.assert_called_once()


@pytest.mark.asyncio
async def test_create_audio_emergency_invalid_format(async_client: AsyncClient, tmp_path: Path) -> None:
    temp_path = tmp_path / "test_emergency_audio.txt"
    temp_path.write_text("dummy text content", encoding="utf-8")

    with temp_path.open("rb") as file_handle:
        files = {"file": ("test_emergency_audio.txt", file_handle, "text/plain")}
        data = {"language": "en"}
        response = await async_client.post("/api/v1/emergency-calls/audio", files=files, data=data)

    assert response.status_code == 422
    assert "Extension .txt not allowed" in response.text


@pytest.mark.asyncio
async def test_create_text_emergency_empty_text(async_client: AsyncClient) -> None:
    payload = {"text": "", "language": "en"}

    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_emergency_calls_envelope(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/emergency-calls/")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["api_version"] == "v1"
