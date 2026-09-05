from app.schemas.emergency_analysis import EmergencyType
from app.services.scoring_policy import calculate_help_required
from app.services.incident_rules import extract_incident_facts, services_for_facts


def services(text: str, kind: EmergencyType, language: str = "en") -> list[str]:
    return [item.value for item in calculate_help_required(
        emergency_type=kind, transcript=text, language=language
    )]


def test_major_railway_accident_has_ambulance_and_police() -> None:
    assert services("major accident at railway station", EmergencyType.ACCIDENT) == [
        "ambulance", "police"
    ]


def test_major_accident_with_injuries_has_ambulance_and_police() -> None:
    assert services("major accident three people injured", EmergencyType.ACCIDENT) == [
        "ambulance", "police"
    ]


def test_trapped_train_accident_adds_fire_and_rescue() -> None:
    assert services("train accident people trapped", EmergencyType.ACCIDENT) == [
        "ambulance", "police", "fire_service", "rescue"
    ]


def test_fire_requires_fire_service_only_without_casualty_evidence() -> None:
    assert services("building fire", EmergencyType.FIRE) == ["fire_service"]


def test_fire_with_trapped_people_adds_ambulance_and_rescue() -> None:
    assert services("building fire people trapped", EmergencyType.FIRE) == [
        "ambulance", "fire_service", "rescue"
    ]


def test_domestic_violence_with_bleeding_adds_ambulance() -> None:
    assert services(
        "my husband beat me and I am bleeding", EmergencyType.DOMESTIC_VIOLENCE
    ) == ["ambulance", "police"]


def test_medical_emergency_has_ambulance() -> None:
    assert services("severe chest pain", EmergencyType.MEDICAL) == ["ambulance"]


def test_specialist_categories_are_supported() -> None:
    assert services("cyber fraud money stolen", EmergencyType.CYBERCRIME) == [
        "police", "cybercrime"
    ]
    assert services("gas leakage in house", EmergencyType.LPG) == ["lpg"]


def test_multilingual_accident_evidence_uses_same_policy() -> None:
    assert "ambulance" in services("गंभीर दुर्घटना में घायल", EmergencyType.ACCIDENT, "hi")
    assert "ambulance" in services("ગંભીર અકસ્માતમાં ઇજા", EmergencyType.ACCIDENT, "gu")
    assert "ambulance" in services("गंभीर अपघात जखमी", EmergencyType.ACCIDENT, "mr")


def test_active_home_intrusion_is_police_only() -> None:
    facts = extract_incident_facts(
        "someone is breaking into my house right now I am scared and need police assistant immediately"
    )
    assert facts.emergency_type == "crime_police"
    assert facts.home_intrusion is True
    assert facts.burglary_in_progress is True
    assert facts.crime_in_progress is True
    assert facts.immediate_danger is True
    assert [item.value for item in services_for_facts(facts)] == ["police"]
    assert facts.weapon_present is False


def test_burglary_does_not_infer_weapon_or_rescue() -> None:
    facts = extract_incident_facts("Someone is breaking into my house right now. I need police.")
    assert facts.weapon_present is False
    assert facts.trapped_persons is False
    assert facts.rescue_required is False
    assert facts.fire_present is False
