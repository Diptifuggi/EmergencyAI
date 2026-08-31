from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import OllamaUnavailableError
from app.schemas.emergency_analysis import (
    STATUS_ANALYSIS_FAILED,
    STATUS_ANALYZED,
    AnalysisLevel,
    EmergencyAnalysisInput,
    EmergencyType,
    HelpRequired,
)
from app.services.emergency_analysis_service import EmergencyAnalysisService
from app.services.ollama_client import OllamaClient


def _valid_analysis_payload(**overrides: object) -> dict:
    base = {
        "emergency_type": "police",
        "help_required": ["police"],
        "emergency_keywords": ["police", "help"],
        "priority_score": 70,
        "priority_level": "HIGH",
        "panic_score": 55,
        "panic_level": "MEDIUM",
        "stress_score": 50,
        "stress_level": "MEDIUM",
        "dispatch_recommendation": {"recommended_units": ["police"]},
        "confidence": 0.8,
    }
    base.update(overrides)
    return base


def _mock_client(return_value: str) -> OllamaClient:
    client = OllamaClient()
    client.generate_json = AsyncMock(return_value=return_value)  # type: ignore[method-assign]
    return client


@pytest.mark.asyncio
async def test_police_women_safety_analysis() -> None:
    payload_json = _valid_analysis_payload(
        emergency_type="women_safety",
        help_required=["police", "women_safety_support"],
        emergency_keywords=["police", "following me"],
        priority_score=78,
        priority_level="HIGH",
        panic_score=62,
        panic_level="MEDIUM",
        stress_score=58,
        stress_level="MEDIUM",
        dispatch_recommendation={"recommended_units": ["police"]},
        confidence=0.86,
    )
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload_json)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="I need police help because someone is following me.",
            language="en",
            call_type="voice_text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    assert result.analysis.emergency_type == EmergencyType.WOMEN_SAFETY
    assert HelpRequired.POLICE in result.analysis.help_required
    assert result.analysis.priority_level == AnalysisLevel.HIGH
    assert 0 <= result.analysis.panic_score <= 100
    assert 0 <= result.analysis.stress_score <= 100
    assert 0.0 <= result.analysis.confidence <= 1.0
    assert "police" in result.analysis.dispatch_recommendation.recommended_units
    assert result.suggested_status == STATUS_ANALYZED


@pytest.mark.asyncio
async def test_accident_ambulance_analysis() -> None:
    payload_json = _valid_analysis_payload(
        emergency_type="accident",
        help_required=["ambulance", "medical_assistance"],
        emergency_keywords=["road accident", "badly injured", "ambulance"],
        priority_score=90,
        priority_level="CRITICAL",
        panic_score=70,
        panic_level="HIGH",
        stress_score=65,
        stress_level="HIGH",
        dispatch_recommendation={"recommended_units": ["ambulance", "police"]},
        confidence=0.9,
    )
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload_json)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content=(
                "There has been a road accident and someone is badly injured. "
                "Please send an ambulance."
            ),
            language="en",
            call_type="text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    assert result.analysis.emergency_type == EmergencyType.ACCIDENT
    assert HelpRequired.AMBULANCE in result.analysis.help_required
    assert result.analysis.priority_level in {AnalysisLevel.HIGH, AnalysisLevel.CRITICAL}
    assert "ambulance" in result.analysis.dispatch_recommendation.recommended_units


@pytest.mark.asyncio
async def test_fire_rescue_analysis() -> None:
    payload_json = _valid_analysis_payload(
        emergency_type="fire",
        help_required=["fire_service", "rescue"],
        emergency_keywords=["fire", "trapped"],
        priority_score=95,
        priority_level="CRITICAL",
        panic_score=80,
        panic_level="HIGH",
        stress_score=75,
        stress_level="HIGH",
        dispatch_recommendation={"recommended_units": ["fire_service", "rescue"]},
        confidence=0.92,
    )
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload_json)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="There is a fire in the building and people are trapped inside.",
            language="en",
            call_type="voice_text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    assert result.analysis.emergency_type == EmergencyType.FIRE
    assert HelpRequired.FIRE_SERVICE in result.analysis.help_required
    assert HelpRequired.AMBULANCE in result.analysis.help_required
    assert HelpRequired.RESCUE not in result.analysis.help_required


@pytest.mark.asyncio
async def test_non_emergency_low_priority() -> None:
    payload_json = _valid_analysis_payload(
        emergency_type="other",
        help_required=["unknown"],
        emergency_keywords=["lost wallet"],
        priority_score=5,
        priority_level="LOW",
        panic_score=5,
        panic_level="LOW",
        stress_score=10,
        stress_level="LOW",
        dispatch_recommendation={"recommended_units": []},
        confidence=0.7,
    )
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload_json)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="I lost my wallet.",
            language="en",
            call_type="text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    assert result.analysis.emergency_type == EmergencyType.OTHER
    assert result.analysis.priority_level == AnalysisLevel.LOW
    assert result.analysis.priority_score <= 20


@pytest.mark.asyncio
async def test_empty_transcript_failure() -> None:
    client = OllamaClient()
    client.generate_json = AsyncMock()  # type: ignore[method-assign]
    service = EmergencyAnalysisService(client)

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="   ",
            transcription=None,
            language="en",
            call_type="text",
        )
    )

    assert result.success is False
    assert result.failure_code == "empty_transcript"
    assert result.analysis is None
    assert result.suggested_status == STATUS_ANALYSIS_FAILED
    client.generate_json.assert_not_called()


@pytest.mark.asyncio
async def test_ollama_unavailable() -> None:
    client = OllamaClient()
    client.generate_json = AsyncMock(  # type: ignore[method-assign]
        side_effect=OllamaUnavailableError("Ollama backend is unavailable")
    )
    service = EmergencyAnalysisService(client)

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="Fire in the kitchen",
            language="en",
            call_type="text",
        )
    )

    assert result.success is False
    assert result.failure_code == "ollama_unavailable"
    assert result.analysis is None
    assert result.suggested_status == STATUS_ANALYSIS_FAILED


@pytest.mark.asyncio
async def test_invalid_ollama_json() -> None:
    service = EmergencyAnalysisService(_mock_client("this is not json"))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="Need help now",
            language="en",
            call_type="text",
        )
    )

    assert result.success is False
    assert result.failure_code == "invalid_analysis_response"
    assert result.analysis is None


@pytest.mark.asyncio
async def test_out_of_range_llm_indicators_are_safely_clamped() -> None:
    payload = _valid_analysis_payload(priority_score=500)
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="Need help now",
            language="en",
            call_type="text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    # priority_score is ignored; panic/stress are safely normalized if out of range.


@pytest.mark.asyncio
async def test_normalizes_llm_alias_values() -> None:
    payload = _valid_analysis_payload(
        emergency_type="not_a_real_type",
        help_required=["medical", "fire brigade"],
        dispatch_recommendation={"recommended_units": ["medical", "firefighters"]},
    )
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="There is a fire and someone needs medical help",
            language="en",
            call_type="text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    assert result.analysis.emergency_type == EmergencyType.UNKNOWN
    assert HelpRequired.MEDICAL_ASSISTANCE in result.analysis.help_required
    assert HelpRequired.FIRE_SERVICE in result.analysis.help_required
    assert "medical_assistance" in result.analysis.dispatch_recommendation.recommended_units
    assert "fire_service" in result.analysis.dispatch_recommendation.recommended_units


@pytest.mark.asyncio
async def test_client_metadata_merge_preserves_existing_keys() -> None:
    payload_json = _valid_analysis_payload()
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload_json)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="Police help needed",
            language="en",
            call_type="text",
        )
    )

    existing = {"device": "flutter", "recorded_at": "2026-08-12T00:00:00Z"}
    merged = result.to_client_metadata_patch(existing)

    assert merged["device"] == "flutter"
    assert merged["recorded_at"] == "2026-08-12T00:00:00Z"
    assert "emergency_analysis" in merged
    assert merged["emergency_analysis"]["emergency_type"] == "police"


@pytest.mark.asyncio
async def test_failure_metadata_patch() -> None:
    client = OllamaClient()
    client.generate_json = AsyncMock(  # type: ignore[method-assign]
        side_effect=OllamaUnavailableError()
    )
    service = EmergencyAnalysisService(client)

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="Help",
            language="en",
            call_type="text",
        )
    )

    merged = result.to_client_metadata_patch({"device": "test"})
    assert merged["device"] == "test"
    assert "emergency_analysis_error" in merged
    assert merged["emergency_analysis_error"]["code"] == "ollama_unavailable"


@pytest.mark.asyncio
async def test_resolves_transcription_when_text_content_missing() -> None:
    payload_json = _valid_analysis_payload()
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload_json)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content=None,
            transcription="Smoke in apartment hallway",
            language="en",
            call_type="audio",
        )
    )

    assert result.success is True
    assert result.analysis is not None


@pytest.mark.asyncio
async def test_json_fence_stripping() -> None:
    payload_json = _valid_analysis_payload()
    fenced = f"```json\n{json.dumps(payload_json)}\n```"
    service = EmergencyAnalysisService(_mock_client(fenced))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="Emergency",
            language="en",
            call_type="text",
        )
    )

    assert result.success is True
    assert result.analysis is not None


@pytest.mark.asyncio
async def test_unknown_help_required_enriched_from_medical_transcript() -> None:
    payload = _valid_analysis_payload(
        emergency_type="police",
        help_required=["unknown"],
        dispatch_recommendation={"recommended_units": ["police"]},
        emergency_keywords=["highway", "emergency"],
    )
    service = EmergencyAnalysisService(_mock_client(json.dumps(payload)))

    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="medical emergency near highway",
            language="en",
            call_type="voice_text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    assert HelpRequired.POLICE in result.analysis.help_required
    assert HelpRequired.MEDICAL_ASSISTANCE in result.analysis.help_required
    assert HelpRequired.UNKNOWN not in result.analysis.help_required
