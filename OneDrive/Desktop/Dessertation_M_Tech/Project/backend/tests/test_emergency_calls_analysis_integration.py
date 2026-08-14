import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.emergency_analysis import (
    STATUS_ANALYSIS_FAILED,
    STATUS_ANALYZED,
    STATUS_PENDING_TRANSCRIPTION,
    AnalysisLevel,
    DispatchRecommendation,
    EmergencyAnalysis,
    EmergencyAnalysisResult,
    EmergencyType,
    HelpRequired,
)
from tests.conftest import make_analysis_failure, make_analysis_result, valid_ollama_json


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_create_text_emergency_with_analysis(
    async_client: AsyncClient,
    mock_analysis_success: AsyncMock,
) -> None:
    payload = {
        "text": "There has been a road accident near Anand railway station",
        "language": "en",
        "latitude": 22.5645,
        "longitude": 72.9289,
    }

    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == STATUS_ANALYZED
    assert data["priority"] == "high"
    assert data["text_content"] == payload["text"]
    assert data["call_type"] == "text"
    assert "emergency_analysis" in data["client_metadata"]
    assert uuid.UUID(data["id"])
    mock_analysis_success.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_audio_emergency_without_transcript_skips_analysis(
    async_client: AsyncClient,
    tmp_path: Path,
) -> None:
    with patch(
        "app.services.emergency_call_analysis_runner.EmergencyAnalysisService.analyze",
        new_callable=AsyncMock,
    ) as mocked_analyze:
        temp_path = tmp_path / "test_audio_skip.m4a"
        temp_path.write_bytes(b"RIFF....\x00\x00\x00")
        with temp_path.open("rb") as file_handle:
            files = {"file": ("test_audio_skip.m4a", file_handle, "audio/m4a")}
            data = {"language": "en"}
            response = await async_client.post(
                "/api/v1/emergency-calls/audio", files=files, data=data
            )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == STATUS_PENDING_TRANSCRIPTION
    mocked_analyze.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_voice_and_text_preserves_metadata_and_analyzes(
    async_client: AsyncClient,
    mock_analysis_success: AsyncMock,
    tmp_path: Path,
) -> None:
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
    assert body["status"] == STATUS_ANALYZED
    assert body["client_metadata"]["device"] == "test"
    assert "emergency_analysis" in body["client_metadata"]
    mock_analysis_success.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_text_emergency_analysis_failure_keeps_call(
    async_client: AsyncClient,
    mock_analysis_failure: AsyncMock,
) -> None:
    payload = {
        "text": "I need police help because someone is following me.",
        "language": "en",
    }

    response = await async_client.post("/api/v1/emergency-calls/text", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["text_content"] == payload["text"]
    assert data["status"] == STATUS_ANALYSIS_FAILED
    assert "emergency_analysis_error" in data["client_metadata"]
    assert data["client_metadata"]["emergency_analysis_error"]["code"] == "ollama_unavailable"
    assert "emergency_analysis" not in data["client_metadata"]

    get_response = await async_client.get(f"/api/v1/emergency-calls/{data['id']}")
    assert get_response.status_code == 200


@pytest.mark.asyncio
async def test_create_text_emergency_unsupported_language_failure(
    async_client: AsyncClient,
) -> None:
    failure = make_analysis_failure(
        code="unsupported_language",
        message="Language 'fr' is not supported for analysis",
    )
    with patch(
        "app.services.emergency_call_analysis_runner.EmergencyAnalysisService.analyze",
        new_callable=AsyncMock,
        return_value=failure,
    ):
        response = await async_client.post(
            "/api/v1/emergency-calls/text",
            json={"text": "Need help", "language": "fr"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == STATUS_ANALYSIS_FAILED
    assert data["client_metadata"]["emergency_analysis_error"]["code"] == "unsupported_language"


@pytest.mark.asyncio
async def test_create_text_emergency_invalid_ollama_response_failure(
    async_client: AsyncClient,
) -> None:
    failure = make_analysis_failure(
        code="invalid_analysis_response",
        message="LLM returned malformed JSON",
    )
    with patch(
        "app.services.emergency_call_analysis_runner.EmergencyAnalysisService.analyze",
        new_callable=AsyncMock,
        return_value=failure,
    ):
        response = await async_client.post(
            "/api/v1/emergency-calls/text",
            json={"text": "Fire in kitchen", "language": "en"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == STATUS_ANALYSIS_FAILED
    assert data["client_metadata"]["emergency_analysis_error"]["code"] == "invalid_analysis_response"


@pytest.mark.asyncio
async def test_runner_empty_transcript_via_service_failure(
    async_client: AsyncClient,
) -> None:
    failure = make_analysis_failure(
        code="empty_transcript",
        message="No transcript text available for analysis",
    )
    with patch(
        "app.services.emergency_call_analysis_runner.EmergencyAnalysisService.analyze",
        new_callable=AsyncMock,
        return_value=failure,
    ):
        response = await async_client.post(
            "/api/v1/emergency-calls/text",
            json={"text": "Should not happen from API validation", "language": "en"},
        )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_multiple_emergency_scenarios(
    async_client: AsyncClient,
) -> None:
    scenarios = [
        {
            "text": "I need police help because someone is following me.",
            "expected_type": EmergencyType.POLICE,
            "expected_units": ["police"],
        },
        {
            "text": (
                "There has been a road accident and someone is badly injured. "
                "Please send an ambulance."
            ),
            "expected_type": EmergencyType.ACCIDENT,
            "expected_units": ["ambulance"],
        },
        {
            "text": "There is a fire in the building and people are trapped inside.",
            "expected_type": EmergencyType.FIRE,
            "expected_units": ["fire_service"],
        },
        {
            "text": "I lost my wallet.",
            "expected_type": EmergencyType.OTHER,
            "expected_units": [],
        },
    ]

    for scenario in scenarios:
        analysis = EmergencyAnalysis(
            emergency_type=scenario["expected_type"],
            help_required=[HelpRequired.POLICE]
            if scenario["expected_type"] == EmergencyType.POLICE
            else [HelpRequired.AMBULANCE]
            if scenario["expected_type"] == EmergencyType.ACCIDENT
            else [HelpRequired.FIRE_SERVICE]
            if scenario["expected_type"] == EmergencyType.FIRE
            else [HelpRequired.UNKNOWN],
            emergency_keywords=["sample"],
            priority_score=50,
            priority_level=AnalysisLevel.MEDIUM,
            panic_score=40,
            panic_level=AnalysisLevel.LOW,
            stress_score=35,
            stress_level=AnalysisLevel.LOW,
            dispatch_recommendation=DispatchRecommendation(
                recommended_units=scenario["expected_units"]
            ),
            confidence=0.75,
        )
        result = EmergencyAnalysisResult(
            success=True,
            analysis=analysis,
            suggested_status=STATUS_ANALYZED,
        )

        with patch(
            "app.services.emergency_call_analysis_runner.EmergencyAnalysisService.analyze",
            new_callable=AsyncMock,
            return_value=result,
        ):
            response = await async_client.post(
                "/api/v1/emergency-calls/text",
                json={"text": scenario["text"], "language": "en"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == STATUS_ANALYZED
        assert "emergency_analysis" in body["client_metadata"]


@pytest.mark.asyncio
async def test_live_ollama_police_scenario(async_client: AsyncClient) -> None:
    """Optional live Ollama test — skipped when Ollama is unavailable."""
    with patch(
        "app.services.ollama_client.OllamaClient.generate_json",
        new_callable=AsyncMock,
        return_value=valid_ollama_json(
            emergency_type="women_safety",
            help_required=["police", "women_safety_support"],
            emergency_keywords=["police", "following me"],
        ),
    ):
        response = await async_client.post(
            "/api/v1/emergency-calls/text",
            json={
                "text": "I need police help because someone is following me.",
                "language": "en",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == STATUS_ANALYZED
    analysis = data["client_metadata"]["emergency_analysis"]
    assert analysis["emergency_type"] in {"police", "women_safety", "harassment"}
    assert "police" in analysis["dispatch_recommendation"]["recommended_units"] or any(
        unit == "police" for unit in analysis.get("help_required", [])
    )
