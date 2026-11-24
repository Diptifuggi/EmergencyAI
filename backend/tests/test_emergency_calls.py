import io
import uuid
import wave
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import map_snapshot_storage
from app.schemas.emergency_analysis import (
    STATUS_ANALYZING,
    STATUS_ANALYZED,
    STATUS_PENDING_TRANSCRIPTION,
)


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


def test_map_snapshot_resolver_is_confined_to_snapshot_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    storage_dir = project_root / "backend" / "storage" / "map_snapshots"
    storage_dir.mkdir(parents=True)
    monkeypatch.setattr(map_snapshot_storage, "BASE_DIR", project_root)
    monkeypatch.setattr(map_snapshot_storage, "MAP_SNAPSHOT_DIR", storage_dir)
    saved_snapshot = storage_dir / "saved.png"
    saved_snapshot.write_bytes(b"image")
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"outside")

    assert map_snapshot_storage.resolve_map_snapshot_path(
        "backend/storage/map_snapshots/saved.png"
    ) == saved_snapshot
    assert map_snapshot_storage.resolve_map_snapshot_path(
        str(outside_file)
    ) is None
    assert map_snapshot_storage.resolve_map_snapshot_path(
        "../../outside.png"
    ) is None


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
    assert data["status"] == STATUS_ANALYZING
    assert data["text_content"] == payload["text"]
    assert data["language"] == "en-IN"
    assert data["requested_language"] == "en-IN"
    assert data["call_type"] == "text"
    assert data["latitude"] == payload["latitude"]
    assert data["longitude"] == payload["longitude"]
    assert data["location_accuracy"] == payload["location_accuracy"]
    assert data["location_timestamp"].startswith("2026-08-27T10:30:00")
    assert data["location_address"] is None
    assert data["location_address_status"] == "pending"
    assert data["location_status"] == "captured"
    assert uuid.UUID(data["id"])
    saved = await async_client.get(f"/api/v1/emergency-calls/{data['id']}")
    assert saved.status_code == 200
    assert saved.json()["location_address"] == "Anand, Gujarat, India"
    assert saved.json()["location_address_status"] == "resolved"
    assert saved.json()["status"] == STATUS_ANALYZED
    assert "emergency_analysis" in saved.json()["client_metadata"]


@pytest.mark.asyncio
async def test_geocoded_addresses_persist_in_detail_and_list_without_relookup(
    async_client: AsyncClient,
) -> None:
    pairs = {
        (12.3456, -45.6789): "Example locality, Example region",
        (-23.4567, 67.8901): "Another locality, Another region",
    }

    async def geocode(latitude: float, longitude: float) -> str:
        return pairs[(latitude, longitude)]

    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(side_effect=geocode),
    ) as mocked_geocode:
        created_calls = []
        for (latitude, longitude), expected_address in pairs.items():
            payload = emergency_text_payload()
            payload.update(latitude=latitude, longitude=longitude)
            created = await async_client.post("/api/v1/emergency-calls/text", json=payload)
            assert created.status_code == 201
            created_calls.append((created.json()["id"], latitude, longitude, expected_address))

        assert mocked_geocode.await_count == 2
        listing = await async_client.get("/api/v1/emergency-calls/")
        assert listing.status_code == 200

        for call_id, latitude, longitude, expected_address in created_calls:
            detail = await async_client.get(f"/api/v1/emergency-calls/{call_id}")
            listed_call = next(
                item for item in listing.json()["items"] if item["id"] == call_id
            )
            for record in (detail.json(), listed_call):
                assert record["latitude"] == latitude
                assert record["longitude"] == longitude
                assert record["location_address"] == expected_address
                assert record["location_address_status"] == "resolved"
                assert record["text_content"] == emergency_text_payload()["text"]
                assert record["priority"] == "critical"
                assert record["source"] == "flutter"
                assert record["location_accuracy"] == 8.5
                assert record["location_timestamp"].startswith("2026-08-27T10:30:00")
                assert record["location_status"] == "captured"

        await async_client.get(f"/api/v1/emergency-calls/{created_calls[0][0]}")
        assert mocked_geocode.await_count == 2

        caller_payload = emergency_text_payload()
        caller_payload.update(
            latitude=12.3456,
            longitude=-45.6789,
            location_address="Caller-reported location",
        )
        caller_report = await async_client.post(
            "/api/v1/emergency-calls/text",
            json=caller_payload,
        )
        caller_id = caller_report.json()["id"]
        updated = await async_client.patch(
            f"/api/v1/emergency-calls/{caller_id}",
            json={"latitude": 13.4567, "longitude": -46.789},
        )
        caller_call = await async_client.get(f"/api/v1/emergency-calls/{caller_id}")
        listed_caller = next(
            item
            for item in (await async_client.get("/api/v1/emergency-calls/")).json()["items"]
            if item["id"] == caller_id
        )
        assert updated.status_code == 200
        assert caller_call.json()["location_address"] == "Caller-reported location"
        assert caller_call.json()["location_address_status"] == "reported"
        assert caller_call.json()["latitude"] == 13.4567
        assert listed_caller["location_address"] == "Caller-reported location"
        assert mocked_geocode.await_count == 2


@pytest.mark.asyncio
async def test_failed_reverse_geocoding_keeps_gps_and_is_not_retried_on_get(
    async_client: AsyncClient,
) -> None:
    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(return_value=None),
    ) as mocked_geocode:
        created = await async_client.post(
            "/api/v1/emergency-calls/text",
            json=emergency_text_payload(),
        )
        call_id = created.json()["id"]
        detail = await async_client.get(f"/api/v1/emergency-calls/{call_id}")
        await async_client.get(f"/api/v1/emergency-calls/{call_id}")

    assert detail.json()["latitude"] == emergency_text_payload()["latitude"]
    assert detail.json()["longitude"] == emergency_text_payload()["longitude"]
    assert detail.json()["location_status"] == "captured"
    assert detail.json()["location_address"] is None
    assert detail.json()["location_address_status"] == "failed"
    assert detail.json()["status"] == STATUS_ANALYZED
    assert detail.json()["text_content"] == emergency_text_payload()["text"]
    mocked_geocode.assert_awaited_once()


@pytest.mark.asyncio
async def test_map_snapshot_is_linked_to_existing_emergency_call(
    async_client: AsyncClient,
    tmp_path: Path,
) -> None:
    storage_dir = tmp_path / "backend" / "storage" / "map_snapshots"
    storage_dir.mkdir(parents=True)
    with (
        patch("app.api.v1.emergency_calls.MAP_SNAPSHOT_DIR", storage_dir),
        patch("app.services.map_snapshot_storage.BASE_DIR", tmp_path),
        patch("app.services.map_snapshot_storage.MAP_SNAPSHOT_DIR", storage_dir),
        patch(
            "app.api.v1.emergency_calls.reverse_geocode",
            new=AsyncMock(return_value=None),
        ),
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

        detail = await async_client.get(f"/api/v1/emergency-calls/{call_id}")
        listing = await async_client.get("/api/v1/emergency-calls/")
        assert detail.json()["map_snapshot_available"] is True
        listed_call = next(item for item in listing.json()["items"] if item["id"] == call_id)
        assert listed_call["map_snapshot_available"] is True

        stored_snapshot = next(storage_dir.iterdir())
        stored_snapshot.unlink()
        missing_detail = await async_client.get(f"/api/v1/emergency-calls/{call_id}")
        missing_listing = await async_client.get("/api/v1/emergency-calls/")
        assert missing_detail.json()["map_snapshot_available"] is False
        missing_listed_call = next(
            item for item in missing_listing.json()["items"] if item["id"] == call_id
        )
        assert missing_listed_call["map_snapshot_available"] is False
        missing_file = await async_client.get(
            f"/api/v1/emergency-calls/{call_id}/map-snapshot"
        )
        assert missing_file.status_code == 404


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
    assert body["status"] == STATUS_ANALYZING
    assert body["client_metadata"]["device"] == "test"
    assert body["audio_url"] is not None
    saved = await async_client.get(f"/api/v1/emergency-calls/{body['id']}")
    assert saved.status_code == 200
    assert saved.json()["status"] == STATUS_ANALYZED
    assert "emergency_analysis" in saved.json()["client_metadata"]


@pytest.mark.asyncio
async def test_audio_update_preserves_existing_location_and_analysis_metadata(
    async_client: AsyncClient,
    tmp_path: Path,
) -> None:
    payload = {
        **emergency_text_payload(),
        "client_metadata": {"device": "flutter-test"},
    }
    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(return_value="Anand, Gujarat, India"),
    ):
        created = await async_client.post(
            "/api/v1/emergency-calls/text",
            json=payload,
        )
    assert created.status_code == 201

    with (
        patch("app.api.v1.emergency_calls.UPLOAD_DIR", tmp_path),
        patch(
            "app.api.v1.emergency_calls.convert_uploaded_audio_to_mp3",
            return_value=(b"ID3" + b"\x00" * 32, ".mp3", "audio/mpeg"),
        ),
        patch(
            "app.api.v1.emergency_calls.reverse_geocode",
            new=AsyncMock(return_value="Anand, Gujarat, India"),
        ),
    ):
        updated = await async_client.post(
            "/api/v1/emergency-calls/audio",
            files={"file": ("voice.wav", b"wav-audio", "audio/wav")},
            data={
                "language": "en",
                "existing_call_id": created.json()["id"],
                "client_metadata": '{"platform":"flutter"}',
            },
        )

    assert updated.status_code == 201
    data = updated.json()
    assert data["latitude"] == payload["latitude"]
    assert data["longitude"] == payload["longitude"]
    assert data["location_accuracy"] == payload["location_accuracy"]
    assert data["location_address"] == "Anand, Gujarat, India"
    assert data["client_metadata"]["device"] == "flutter-test"
    assert data["client_metadata"]["platform"] == "flutter"
    assert "emergency_analysis" in data["client_metadata"]


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
async def test_unavailable_location_does_not_invent_a_permission_reason(
    async_client: AsyncClient,
) -> None:
    response = await async_client.post(
        "/api/v1/emergency-calls/text",
        json={"text": "No location details were provided", "language": "en"},
    )
    assert response.status_code == 201
    assert response.json()["location"]["location_available"] is False
    assert response.json()["location"]["reason"] is None


@pytest.mark.asyncio
async def test_partial_update_preserves_location_and_merges_metadata(
    async_client: AsyncClient,
) -> None:
    payload = {
        **emergency_text_payload(),
        "client_metadata": {"device": "flutter-test"},
    }
    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(return_value="Anand, Gujarat, India"),
    ):
        created = await async_client.post(
            "/api/v1/emergency-calls/text",
            json=payload,
        )
    assert created.status_code == 201
    call_id = created.json()["id"]

    with patch(
        "app.api.v1.emergency_calls.reverse_geocode",
        new=AsyncMock(return_value="Anand, Gujarat, India"),
    ):
        updated = await async_client.patch(
            f"/api/v1/emergency-calls/{call_id}",
            json={
                "latitude": None,
                "longitude": None,
                "location_accuracy": None,
                "location_timestamp": None,
                "client_metadata": {
                    "device": None,
                    "platform": "updated-client",
                },
            },
        )

        assert updated.status_code == 200
        data = updated.json()
        assert data["latitude"] == payload["latitude"]
        assert data["longitude"] == payload["longitude"]
        assert data["location_accuracy"] == payload["location_accuracy"]
        assert data["location_timestamp"].startswith("2026-08-27T10:30:00")
        assert data["location_address"] == "Anand, Gujarat, India"
        assert data["client_metadata"]["device"] == "flutter-test"
        assert data["client_metadata"]["platform"] == "updated-client"
        assert "emergency_analysis" in data["client_metadata"]

        incomplete = await async_client.patch(
            f"/api/v1/emergency-calls/{call_id}",
            json={"latitude": 23.0, "longitude": None},
        )
    assert incomplete.status_code == 200
    assert incomplete.json()["latitude"] == 23.0
    assert incomplete.json()["longitude"] == payload["longitude"]


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
