from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.core.language import bcp47_language, sarvam_language_code
from app.schemas.emergency_analysis import EmergencyAnalysisInput, EmergencyType, HelpRequired
from app.services.emergency_analysis_service import EmergencyAnalysisService
from app.services.ollama_client import OllamaClient
from app.services.incident_rules import extract_incident_facts, services_for_facts


def _client(payload: dict) -> OllamaClient:
    client = OllamaClient()
    client.generate_json = AsyncMock(return_value=json.dumps(payload))  # type: ignore[method-assign]
    return client


def _payload() -> dict:
    return {
        "emergency_type": "police",
        "help_required": ["police", "child_protection"],
        "child_involved": True,
        "children_involved": True,
        "victim_count": 4,
        "priority_score": 99,
        "panic_score": 100,
        "stress_score": 100,
        "dispatch_recommendation": {"recommended_units": ["child_protection"]},
        "confidence": 0.99,
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [("en", "en-IN"), ("hi-IN", "hi-IN"), ("gu", "gu-IN"), ("mr", "mr-IN")],
)
def test_language_normalization(value: str, expected: str) -> None:
    assert bcp47_language(value) == expected
    assert sarvam_language_code(value) == expected


def test_auto_language_is_provider_unknown_not_detected_auto() -> None:
    assert sarvam_language_code("auto") == "unknown"
    assert bcp47_language("auto") is None


@pytest.mark.asyncio
async def test_unsupported_llm_facts_are_not_promoted_to_dispatch() -> None:
    service = EmergencyAnalysisService(_client(_payload()))
    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="રેલવે સ્ટેશન પાસે મોટો અકસ્માત થયો છે.",
            language="gu-IN",
            call_type="text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    analysis = result.analysis
    assert analysis.emergency_type == EmergencyType.ACCIDENT
    assert analysis.railway_incident is True
    assert analysis.child_involved is False
    assert analysis.children_involved is False
    assert analysis.victim_count == 1
    assert analysis.victim_count_source == "default"
    assert analysis.help_required == [HelpRequired.POLICE, HelpRequired.AMBULANCE]
    assert analysis.recommended_units == ["police", "ambulance"]
    assert analysis.dispatch_recommendation.recommended_units == ["police", "ambulance"]
    assert analysis.dispatch_recommendation.emergency_numbers == {
        "100": "Police",
        "108": "Ambulance / Medical Emergency",
        "102": "Ambulance / Medical Emergency",
        "139": "Railway Assistance",
    }
    assert analysis.location_description == "રેલવે સ્ટેશન"
    assert analysis.panic_score is None
    assert analysis.panic_level is None
    assert analysis.stress_score is None
    assert analysis.stress_level is None
    assert analysis.confidence is None
    assert analysis.human_confirmation_required is True


@pytest.mark.asyncio
async def test_hypothetical_accident_is_not_active() -> None:
    service = EmergencyAnalysisService(_client(_payload()))
    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="જો અકસ્માત થાય તો શું કરવું?",
            language="gu-IN",
            call_type="text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    assert result.analysis.emergency_type == EmergencyType.UNKNOWN
    assert result.analysis.railway_incident is False
    assert result.analysis.help_required == []
    assert result.analysis.dispatch_recommendation.recommended_units == []


def test_hindi_railway_count_location_request_and_no_road_inference() -> None:
    facts = extract_incident_facts(
        "आनंद रेलवे स्टेशन पे ट्रेन हादसा हुआ है 25 लोग घायल है मदद भेजे", "hi"
    )
    assert facts.emergency_type == "accident"
    assert facts.sub_type == "railway_accident"
    assert facts.railway_incident is True
    assert facts.road_accident is False
    assert facts.victim_count == 25
    assert facts.injuries_present is True
    assert facts.location_description == "आनंद रेलवे स्टेशन"
    assert facts.caller_request == "मदद भेजे"
    assert services_for_facts(facts).count(HelpRequired.AMBULANCE) == 1
    assert HelpRequired.POLICE in services_for_facts(facts)


def test_explicit_child_injury_is_supported() -> None:
    facts = extract_incident_facts("एक बच्चा घायल है, मदद भेजो", "hi")
    assert facts.children_involved is True
    assert facts.injuries_present is True
    assert facts.caller_request == "मदद भेजो"
    assert HelpRequired.AMBULANCE in services_for_facts(facts)
    assert HelpRequired.CHILD_PROTECTION in services_for_facts(facts)


def test_historical_train_accident_is_not_current_dispatch() -> None:
    facts = extract_incident_facts("कल आनंद में ट्रेन हादसा हुआ था", "hi")
    assert facts.historical is True
    assert facts.current_emergency is False
    assert facts.railway_incident is True
    assert services_for_facts(facts) == []


def test_current_train_accident_with_unspecified_many_injured() -> None:
    facts = extract_incident_facts(
        "अभी ट्रेन हादसा हुआ है और कई लोग घायल हैं", "hi"
    )
    assert facts.current_emergency is True
    assert facts.railway_incident is True
    assert facts.injuries_present is True
    assert facts.victim_count == 5


def test_hindi_number_word_request_and_keywords() -> None:
    facts = extract_incident_facts(
        "आनंद रेलवे स्टेशन के पास ट्रेन अकस्मात हुआ है। मदद चाहिए। पच्चीस लोग घायल हैं।",
        "hi",
    )
    assert facts.victim_count == 25
    assert facts.injuries_present is True
    assert facts.caller_request == "मदद चाहिए"
    assert facts.railway_incident is True
    assert facts.road_accident is False
    assert "घायल" in facts.emergency_keywords
    assert "ट्रेन" in facts.emergency_keywords
