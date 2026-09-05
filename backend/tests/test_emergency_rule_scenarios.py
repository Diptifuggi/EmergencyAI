from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import OllamaUnavailableError
from app.schemas.emergency_analysis import EmergencyAnalysisInput, HelpRequired
from app.services.emergency_analysis_service import EmergencyAnalysisService


async def analyze_without_ollama(text: str):
    client = AsyncMock()
    client.generate_json.side_effect = OllamaUnavailableError("offline")
    return await EmergencyAnalysisService(client).analyze(
        EmergencyAnalysisInput(text_content=text, language="en", call_type="text")
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "emergency_type", "required", "forbidden"),
    [
        (
            "My father is having severe chest pain and is having difficulty breathing. Please send an ambulance immediately.",
            "medical",
            {"ambulance", "medical_assistance"},
            {"fire_service", "rescue"},
        ),
        (
            "There has been a major road accident near the railway station. Several people are injured and need medical help.",
            "accident",
            {"ambulance", "medical_assistance", "police"},
            {"fire_service", "rescue"},
        ),
        (
            "A building is on fire and there are people trapped inside.",
            "fire",
            {"fire_service", "rescue", "ambulance"},
            set(),
        ),
        (
            "Someone is breaking into my house right now. I need police.",
            "crime_police",
            {"police"},
            {"ambulance", "fire_service", "rescue"},
        ),
        (
            "Someone is threatening me with a gun outside my house.",
            "crime_police",
            {"police"},
            {"ambulance", "fire_service"},
        ),
        (
            "My child is missing and I cannot find him.",
            "child_safety",
            {"police", "child_protection"},
            {"fire_service", "ambulance"},
        ),
        (
            "Someone stole money from my bank account through an online scam.",
            "cybercrime",
            {"cybercrime"},
            {"fire_service", "ambulance", "police"},
        ),
        (
            "I smell gas from my LPG cylinder.",
            "lpg",
            {"lpg"},
            {"fire_service", "ambulance"},
        ),
    ],
)
async def test_requested_emergency_scenarios_use_evidence_only(
    text: str, emergency_type: str, required: set[str], forbidden: set[str]
) -> None:
    result = await analyze_without_ollama(text)

    assert result.success is True
    assert result.analysis is not None
    assert result.analysis.emergency_type.value == emergency_type
    units = set(result.analysis.dispatch_recommendation.recommended_units)
    assert required <= units
    assert not forbidden & units


@pytest.mark.asyncio
async def test_active_home_intrusion_has_unified_and_police_numbers() -> None:
    result = await analyze_without_ollama(
        "someone is breaking into my house right now I am scared and need police assistant immediately"
    )

    assert result.analysis is not None
    assert result.analysis.priority_level.value == "HIGH"
    assert result.analysis.immediate_danger is True
    assert result.analysis.crime_in_progress is True
    assert result.analysis.home_intrusion is True
    assert result.analysis.burglary_in_progress is True
    assert result.analysis.dispatch_recommendation.emergency_numbers == {
        "112": "Integrated Emergency Response",
        "100": "Police",
    }
