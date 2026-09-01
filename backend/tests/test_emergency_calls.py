import io
import uuid
import wave
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
        "location_accuracy": 8.5,
        "location_timestamp": "2026-08-27T10:30:00Z",
    }


def valid_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * 800)
    return buffer.getvalue()


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

    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(return_value="Anand, Gujarat, India"),
    ):
        response = await async_client.post("/api/v1/emergency-calls/text", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == STATUS_ANALYZED
    assert data["text_content"] == payload["text"]
    assert data["language"] == payload["language"]
    assert data["call_type"] == "text"
    assert data["latitude"] == payload["latitude"]
    assert data["longitude"] == payload["longitude"]
    assert data["location_accuracy"] == payload["location_accuracy"]
    assert data["location_timestamp"].startswith("2026-08-27T10:30:00")
    assert data["location_address"] == "Anand, Gujarat, India"
    assert data["location_status"] == "captured"
    assert "emergency_analysis" in data["client_metadata"]
    assert uuid.UUID(data["id"])


@pytest.mark.asyncio
async def test_map_snapshot_is_linked_to_existing_emergency_call(
    async_client: AsyncClient,
) -> None:
    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(return_value=None),
    ):
        created = await async_client.post(
            "/api/v1/emergency-calls/text",
            json=emergency_text_payload(),
        )
    assert created.status_code == 201
    call_id = created.json()["id"]
    snapshot = b"fake-png-payload"

    uploaded = await async_client.post(
        f"/api/v1/emergency-calls/{call_id}/map-snapshot",
        files={"map_snapshot": ("caller-map.png", snapshot, "image/png")},
    )

    assert uploaded.status_code == 200
    body = uploaded.json()
    assert body["id"] == call_id
    assert body["map_snapshot_available"] is True
    assert body["map_snapshot_content_type"] == "image/png"
    assert body["map_snapshot_url"].endswith(f"/{call_id}/map-snapshot")

    retrieved = await async_client.get(f"/api/v1/emergency-calls/{call_id}/map-snapshot")
    assert retrieved.status_code == 200
    assert retrieved.headers["content-type"] == "image/png"
    assert retrieved.content == snapshot


@pytest.mark.asyncio
async def test_create_audio_emergency(async_client: AsyncClient, tmp_path: Path) -> None:
    temp_path = tmp_path / "test_emergency_audio.wav"
    temp_path.write_bytes(valid_wav_bytes())

    with temp_path.open("rb") as file_handle:
        files = {"file": ("test_emergency_audio.wav", file_handle, "audio/wav")}
        data = {"language": "en"}
        response = await async_client.post("/api/v1/emergency-calls/audio", files=files, data=data)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == STATUS_PENDING_TRANSCRIPTION
    assert data["call_type"] == "audio"
    assert data["audio_file_path"] is not None
    assert data["original_audio_filename"] == "test_emergency_audio.wav"
    assert data["audio_url"] is not None
    stored_path = Path(data["audio_file_path"])
    assert stored_path.exists()
    assert stored_path.stat().st_size > 14
    assert data["audio_file_size"] == stored_path.stat().st_size


@pytest.mark.asyncio
async def test_create_audio_rejects_placeholder_bytes(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/emergency-calls/audio",
        files={"file": ("placeholder.mp3", b"fake-mp3-bytes", "audio/mpeg")},
        data={"language": "en"},
    )
    assert response.status_code == 400
    assert "valid audio header" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_voice_and_text(async_client: AsyncClient, tmp_path: Path) -> None:
    temp_path = tmp_path / "voice.wav"
    temp_path.write_bytes(valid_wav_bytes())

    with temp_path.open("rb") as file_handle:
        files = {"file": ("voice.wav", file_handle, "audio/wav")}
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
        return_value=(b"ID3" + b"\x00" * 32, ".mp3", "audio/mpeg"),
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
async def test_create_text_emergency_succeeds_when_geocoder_is_down(
    async_client: AsyncClient,
) -> None:
    payload = emergency_text_payload()
    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(return_value=None),
    ):
        response = await async_client.post("/api/v1/emergency-calls/text", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["latitude"] == payload["latitude"]
    assert data["longitude"] == payload["longitude"]
    assert data["location_address"] is None


@pytest.mark.asyncio
async def test_list_emergency_calls_envelope(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/emergency-calls/")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["api_version"] == "v1"


def test_convert_uploaded_audio_to_mp3_real_or_mocked_ffmpeg() -> None:
    from app.api.v1.emergency_calls import convert_uploaded_audio_to_mp3
    import subprocess
    from unittest.mock import MagicMock

    # We mock subprocess.run to verify how it gets called and that it receives files
    # that are not locked.
    called_args = []

    def mock_subprocess_run(args, **kwargs):
        called_args.append(args)
        # Check if the temporary source and output file paths exist
        source_file_path = args[3]
        dest_file_path = args[13]
        
        # Verify that we can write to the dest path or check they exist
        assert Path(source_file_path).exists()
        assert Path(dest_file_path).exists()
        
        # Write some fake output to destination to simulate successful conversion
        Path(dest_file_path).write_bytes(b"mocked-converted-mp3-bytes")
        
        # Return completed process with returncode 0
        mock_res = MagicMock()
        mock_res.returncode = 0
        return mock_res

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        # We also mock _resolve_ffmpeg_path to ensure it returns a dummy path if none is present
        with patch("app.api.v1.emergency_calls._resolve_ffmpeg_path", return_value="dummy_ffmpeg"):
            res_bytes, res_ext, res_mime = convert_uploaded_audio_to_mp3(
                b"fake-original-audio-bytes", "test_file.mp4"
            )
            assert res_bytes == b"mocked-converted-mp3-bytes"
            assert res_ext == ".mp3"
            assert res_mime == "audio/mpeg"

    assert len(called_args) == 1


@pytest.mark.asyncio
async def test_create_text_emergency_validation(async_client: AsyncClient) -> None:
    # Invalid latitude
    payload = emergency_text_payload()
    payload["latitude"] = 999.0
    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)
    assert response.status_code == 422

    # Invalid longitude
    payload = emergency_text_payload()
    payload["longitude"] = -200.0
    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)
    assert response.status_code == 422

    # Invalid accuracy
    payload = emergency_text_payload()
    payload["location_accuracy"] = -5.0
    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_audio_emergency_validation(async_client: AsyncClient, tmp_path: Path) -> None:
    temp_path = tmp_path / "test.m4a"
    temp_path.write_bytes(b"fake-audio")

    # Invalid latitude Form param
    with patch(
        "app.api.v1.emergency_calls.convert_uploaded_audio_to_mp3",
        return_value=(b"fake-mp3-bytes", ".mp3", "audio/mpeg"),
    ):
        with temp_path.open("rb") as file_handle:
            files = {"file": ("test.m4a", file_handle, "audio/m4a")}
            data = {"language": "en", "latitude": "999"}
            response = await async_client.post("/api/v1/emergency-calls/audio", files=files, data=data)
            assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_voice_text_emergency_validation(async_client: AsyncClient, tmp_path: Path) -> None:
    temp_path = tmp_path / "test.m4a"
    temp_path.write_bytes(b"fake-audio")

    # Invalid longitude Form param
    with patch(
        "app.api.v1.emergency_calls.convert_uploaded_audio_to_mp3",
        return_value=(b"fake-mp3-bytes", ".mp3", "audio/mpeg"),
    ):
        with temp_path.open("rb") as file_handle:
            files = {"file": ("test.m4a", file_handle, "audio/m4a")}
            data = {
                "language": "en",
                "transcription": "Help!",
                "longitude": "200.0"
            }
            response = await async_client.post("/api/v1/emergency-calls/voice-text", files=files, data=data)
            assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_text_emergency_location_unavailable(async_client: AsyncClient) -> None:
    payload = {
        "text": "Location is disabled on my device",
        "language": "en",
        "client_metadata": {"location_error": "Location permission denied"}
    }
    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["location"]["location_available"] is False
    assert data["location_status"] == "unavailable"
    assert data["location"]["status"] == "unavailable"
    assert data["location"]["reason"] == "Location permission denied"


@pytest.mark.asyncio
async def test_create_text_emergency_location_available(async_client: AsyncClient) -> None:
    payload = emergency_text_payload()
    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(return_value="Anand Railway Station"),
    ):
        response = await async_client.post("/api/v1/emergency-calls/text", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["location"]["location_available"] is True
    assert data["location_status"] == "captured"
    assert data["location"]["status"] == "captured"
    assert data["location"]["latitude"] == payload["latitude"]
    assert data["location"]["longitude"] == payload["longitude"]
    assert data["location"]["accuracy_meters"] == payload["location_accuracy"]
    assert data["location"]["captured_at"].startswith("2026-08-27T10:30:00")


