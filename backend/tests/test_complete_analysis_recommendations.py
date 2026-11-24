from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.schemas.emergency_analysis import EmergencyAnalysis, EmergencyAnalysisInput
from app.services.emergency_analysis_service import EmergencyAnalysisService
from app.services.ollama_client import OllamaClient


async def analyze_report(text: str, language: str = "en"):
    client = OllamaClient()
    client.generate_json = AsyncMock(  # type: ignore[method-assign]
        return_value=json.dumps({"emergency_type": "unknown"})
    )
    return await EmergencyAnalysisService(client).analyze(
        EmergencyAnalysisInput(
            text_content=text,
            language=language,
            call_type="text",
        )
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "language", "expected_type", "help_values", "units", "contacts"),
    [
        (
            "My father has severe chest pain and difficulty breathing.",
            "en",
            "medical",
            {"ambulance", "medical_assistance"},
            {"ambulance", "medical_assistance"},
            {"112", "108", "102"},
        ),
        (
            "मुझे चेस्ट में दर्द हो रहा है।",
            "hi",
            "medical",
            {"ambulance", "medical_assistance"},
            {"ambulance", "medical_assistance"},
            {"112", "108", "102"},
        ),
        (
            "મારા પિતાને છાતીમાં દુખાવો છે.",
            "gu",
            "medical",
            {"ambulance", "medical_assistance"},
            {"ambulance", "medical_assistance"},
            {"112", "108", "102"},
        ),
        (
            "माझ्या वडिलांना हृदयविकाराचा झटका आला आहे.",
            "mr",
            "medical",
            {"ambulance", "medical_assistance"},
            {"ambulance", "medical_assistance"},
            {"112", "108", "102"},
        ),
        (
            "I smell gas from my LPG cylinder.",
            "en",
            "lpg",
            {"lpg"},
            set(),
            {"112", "1906"},
        ),
        (
            "There is a building fire and people are trapped inside.",
            "en",
            "fire",
            {"ambulance", "fire_service", "rescue"},
            {"ambulance", "fire_service", "rescue"},
            {"112", "108", "102", "101"},
        ),
        (
            "Someone stole money from my bank account through an online scam.",
            "en",
            "cybercrime",
            {"cybercrime"},
            set(),
            {"1930"},
        ),
        (
            "My child is missing and I need police.",
            "en",
            "child_safety",
            {"police", "child_protection"},
            {"police", "child_protection"},
            {"100", "1098"},
        ),
        (
            "A major accident happened on the highway; three people are injured.",
            "en",
            "accident",
            {"ambulance", "medical_assistance"},
            {"ambulance", "medical_assistance"},
            {"112", "108", "102", "1033"},
        ),
        (
            "Flood water is rising and 20 people are trapped.",
            "en",
            "disaster",
            {"rescue"},
            {"rescue"},
            {"112", "1070", "1077"},
        ),
    ],
)
async def test_supported_reports_return_complete_evidence_based_analysis(
    text: str,
    language: str,
    expected_type: str,
    help_values: set[str],
    units: set[str],
    contacts: set[str],
) -> None:
    result = await analyze_report(text, language)

    assert result.success is True
    assert result.analysis is not None
    analysis = result.analysis
    data = analysis.model_dump()

    assert set(data) == set(EmergencyAnalysis.model_fields)
    assert analysis.emergency_type.value == expected_type
    assert help_values <= {item.value for item in analysis.help_required}
    assert units <= set(analysis.recommended_units)
    assert analysis.recommended_units == analysis.dispatch_recommendation.recommended_units
    assert contacts <= set(analysis.dispatch_recommendation.emergency_numbers)
    assert analysis.dispatch_recommendation.reason
    assert analysis.dispatch_recommendation.priority_reason
    assert analysis.dispatch_recommendation.dispatcher_action
    assert analysis.human_confirmation_required is True
    assert analysis.confidence is None
    assert analysis.panic_score is None and analysis.panic_level is None
    assert analysis.stress_score is None and analysis.stress_level is None


@pytest.mark.asyncio
async def test_lpg_and_cybercrime_assistance_does_not_invent_response_units() -> None:
    for text, expected_help in (
        ("I smell gas from my LPG cylinder.", "lpg"),
        ("Someone stole money from my bank account through an online scam.", "cybercrime"),
    ):
        result = await analyze_report(text)

        assert result.analysis is not None
        assert {item.value for item in result.analysis.help_required} == {expected_help}
        assert result.analysis.recommended_units == []
        assert "No operational unit is mapped" in (
            result.analysis.dispatch_recommendation.reason
        )
        assert "Human operator confirmation is required" in (
            result.analysis.dispatch_recommendation.dispatcher_action
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "context_state"),
    [
        ("There is no fire and nobody is injured.", "negated"),
        ("There was a fire yesterday, but it is out and everyone is safe now.", "resolved"),
        ("Maybe there is a fire; I am not sure.", "uncertain"),
    ],
)
async def test_non_current_or_ambiguous_reports_request_clarification(
    text: str, context_state: str
) -> None:
    result = await analyze_report(text)

    assert result.analysis is not None
    analysis = result.analysis
    assert analysis.context_state == context_state
    assert analysis.current_emergency is False
    assert analysis.priority_score == 0
    assert analysis.dispatch_recommendation.recommended_units == []
    assert analysis.dispatch_recommendation.emergency_numbers == {}
    assert "Confirm whether the report describes a current incident" in (
        analysis.dispatch_recommendation.dispatcher_action
    )
