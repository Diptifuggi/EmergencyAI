import pytest
from pydantic import ValidationError

from app.schemas.emergency_analysis import EmergencyAnalysis, EmergencyType, HelpRequired
from app.services.scoring_policy import (
    calculate_help_required,
    calculate_priority_score,
    calculate_severity_score,
    clamp_score,
    level_for_score,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0, "LOW"), (25, "LOW"), (26, "MEDIUM"), (50, "MEDIUM"),
     (51, "HIGH"), (75, "HIGH"), (76, "CRITICAL"), (100, "CRITICAL")],
)
def test_score_boundaries_use_fixed_levels(score: int, expected: str) -> None:
    # The same policy deliberately applies to both priority and stress.
    assert level_for_score(score).value == expected


@pytest.mark.parametrize(("score", "expected"), [(-1, 0), (101, 100)])
def test_model_scores_are_safely_clamped(score: int, expected: int) -> None:
    assert clamp_score(score) == expected


def test_schema_rejects_inconsistent_priority_and_stress_levels() -> None:
    payload = {
        "emergency_type": "police", "priority_score": 10, "priority_level": "HIGH",
        "panic_score": 10, "panic_level": "LOW", "stress_score": 45,
        "stress_level": "LOW", "dispatch_recommendation": {"recommended_units": []},
        "confidence": 0.5,
    }
    with pytest.raises(ValidationError):
        EmergencyAnalysis.model_validate(payload)


@pytest.mark.parametrize("field", ["priority_score", "stress_score"])
@pytest.mark.parametrize("value", [-1, 101])
def test_final_schema_rejects_out_of_range_scores(field: str, value: int) -> None:
    payload = {
        "emergency_type": "police", "priority_score": 10, "priority_level": "LOW",
        "panic_score": 10, "panic_level": "LOW", "stress_score": 10,
        "stress_level": "LOW", "dispatch_recommendation": {"recommended_units": []},
        "confidence": 0.5,
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        EmergencyAnalysis.model_validate(payload)


@pytest.mark.parametrize(
    ("transcript", "emergency_type", "minimum_level", "expected_help"),
    [
        ("I had a small road accident. Nobody is injured and we need some assistance.", EmergencyType.ACCIDENT, "LOW", [HelpRequired.UNKNOWN]),
        ("Major accident near Vapi Main Highway. Several people are injured and need immediate medical help.", EmergencyType.ACCIDENT, "HIGH", [HelpRequired.AMBULANCE]),
        ("Major accident near Vapi Main Highway. A vehicle is on fire and people are trapped.", EmergencyType.ACCIDENT, "CRITICAL", [HelpRequired.AMBULANCE, HelpRequired.FIRE_SERVICE, HelpRequired.RESCUE]),
        ("Someone is following me while I am walking alone. I am scared. Please send police.", EmergencyType.POLICE, "HIGH", [HelpRequired.POLICE]),
        ("My father has severe chest pain and needs an ambulance immediately.", EmergencyType.MEDICAL, "CRITICAL", [HelpRequired.AMBULANCE]),
        ("There is a fire in a building and people are trapped inside.", EmergencyType.FIRE, "CRITICAL", [HelpRequired.AMBULANCE, HelpRequired.FIRE_SERVICE, HelpRequired.RESCUE]),
        ("I lost my phone and need help finding it.", EmergencyType.OTHER, "LOW", [HelpRequired.UNKNOWN]),
    ],
)
def test_research_scenarios_have_consistent_priority(
    transcript: str, emergency_type: EmergencyType, minimum_level: str,
    expected_help: list[HelpRequired],
) -> None:
    score = calculate_priority_score(
        emergency_type=emergency_type, immediate_threat=False,
        people_at_risk=0, transcript=transcript,
    )
    assert level_for_score(score).value == minimum_level
    assert calculate_help_required(emergency_type=emergency_type, transcript=transcript) == expected_help


@pytest.mark.parametrize(
    ("transcript", "language", "emergency_type", "minimum_score"),
    [
        ("My father is unconscious", "en", EmergencyType.MEDICAL, 76),
        ("मेरी मां बेहोश हैं", "hi", EmergencyType.MEDICAL, 76),
        ("મારા પિતાને છાતીમાં દુખાવો છે", "gu", EmergencyType.MEDICAL, 76),
        ("माझ्या वडिलांना हृदयविकाराचा झटका आला आहे", "mr", EmergencyType.MEDICAL, 76),
        ("There is an explosion in the building", "en", EmergencyType.FIRE, 76),
        ("A gas leak is active in the kitchen", "en", EmergencyType.LPG, 51),
    ],
)
def test_high_risk_evidence_sets_urgent_human_review_floor(
    transcript: str,
    language: str,
    emergency_type: EmergencyType,
    minimum_score: int,
) -> None:
    score = calculate_priority_score(
        emergency_type=emergency_type,
        immediate_threat=False,
        people_at_risk=0,
        transcript=transcript,
        language=language,
    )

    assert score >= minimum_score


def test_active_heart_risk_changes_severity_independently_of_llm_values() -> None:
    score = calculate_severity_score(
        emergency_type=EmergencyType.MEDICAL,
        transcript="My mother is not breathing.",
    )

    assert level_for_score(score).value == "CRITICAL"
