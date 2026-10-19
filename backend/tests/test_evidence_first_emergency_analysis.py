from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.schemas.emergency_analysis import EmergencyAnalysisInput, HelpRequired
from app.services.emergency_analysis_service import EmergencyAnalysisService
from app.services.incident_rules import extract_incident_facts, services_for_facts
from app.services.ollama_client import OllamaClient


def _client() -> OllamaClient:
    client = OllamaClient()
    client.generate_json = AsyncMock(return_value=json.dumps({"emergency_type": "unknown"}))  # type: ignore[method-assign]
    return client


def test_flood_risk_is_not_confirmed_flood_or_entrapment() -> None:
    facts = extract_incident_facts(
        "વાપી એરિયામાં બહુ જ ભારે વરસાદ પડે છે એના લીધે પૂરની શક્યતા છે.", "gu"
    )

    assert facts.location_description == "વાપી વિસ્તાર"
    assert facts.heavy_rain is True
    assert facts.flood_risk is True
    assert facts.flood_confirmed is False
    assert [(item.concept, item.certainty) for item in facts.evidence] == [
        ("heavy_rain", "confirmed"),
        ("flood", "possible"),
    ]
    assert facts.context_state == "potential_risk"
    assert facts.current_emergency is False
    assert facts.trapped_persons is False
    assert facts.rescue_required is False
    assert facts.victim_count is None
    assert services_for_facts(facts) == []


def test_confirmed_flood_only_adds_rescue_when_people_are_trapped() -> None:
    facts = extract_incident_facts("વાપીમાં પૂર આવ્યું છે.", "gu")
    assert facts.flood_confirmed is True
    assert facts.current_emergency is True
    assert facts.trapped_persons is False
    assert facts.rescue_required is False

    trapped = extract_incident_facts("વાપીમાં પૂર આવ્યું છે અને 20 લોકો ફસાયા છે.", "gu")
    assert trapped.flood_confirmed is True
    assert trapped.trapped_persons is True
    assert trapped.victim_count == 20
    assert trapped.rescue_required is True
    assert HelpRequired.RESCUE in services_for_facts(trapped)


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        ("पच्चीस लोग घायल हैं", "hi", 25),
        ("૨૫ લોકો ઘાયલ થયા છે", "gu", 25),
        ("पंचवीस लोक जखमी झाले आहेत", "mr", 25),
    ],
)
def test_multilingual_explicit_counts_are_preserved(
    text: str, language: str, expected: int
) -> None:
    facts = extract_incident_facts(text, language)
    assert facts.victim_count == expected
    assert facts.injuries_present is True


def test_explosion_does_not_invent_fire_injury_or_trapped_people() -> None:
    facts = extract_incident_facts(
        "विद्यानगर में कॉलेज की कैंटीन में एलपीजी गैस ब्लास्ट हुआ है, मदद चाहिए।", "hi"
    )
    assert facts.explosion_present is True
    assert facts.lpg_leak is True
    assert facts.fire_present is False
    assert facts.injuries_present is False
    assert facts.trapped_persons is False
    assert facts.rescue_required is False
    assert facts.location_description == "विद्यानगर, कॉलेज कैंटीन"
    assert facts.caller_request == "मदद चाहिए"


def test_context_invariants() -> None:
    hypothetical = extract_incident_facts("अगर आग लग जाए तो क्या करना चाहिए?", "hi")
    historical = extract_incident_facts("कल आग लगी थी", "hi")
    negated = extract_incident_facts("गैस सिलेंडर नहीं फटा है", "hi")
    uncertain = extract_incident_facts("शायद गैस सिलेंडर फट गया है", "hi")

    assert hypothetical.current_emergency is False
    assert historical.current_emergency is False
    assert negated.explosion_present is False
    assert negated.negated is True
    assert uncertain.uncertain is True
    assert uncertain.explosion_present is True
    assert uncertain.current_emergency is False


@pytest.mark.asyncio
async def test_final_analysis_ignores_hallucinated_llm_fields_for_risk() -> None:
    service = EmergencyAnalysisService(_client())
    result = await service.analyze(
        EmergencyAnalysisInput(
            text_content="વાપી એરિયામાં બહુ જ ભારે વરસાદ પડે છે એના લીધે પૂરની શક્યતા છે.",
            language="gu-IN",
            call_type="text",
        )
    )

    assert result.success is True
    assert result.analysis is not None
    analysis = result.analysis
    assert analysis.context_state == "potential_risk"
    assert analysis.current_emergency is False
    assert analysis.flood_risk is True
    assert analysis.flood_confirmed is False
    assert analysis.trapped_persons is False
    assert analysis.rescue_required is False
    assert analysis.recommended_units == []
    assert analysis.priority_score == 0