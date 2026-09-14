from __future__ import annotations

import pytest

from app.schemas.emergency_analysis import HelpRequired
from app.services.incident_rules import extract_incident_facts, services_for_facts


@pytest.mark.parametrize(
    ("text", "language", "field", "expected"),
    [
        ("Help help help, someone please come", "en", "caller_request", "help"),
        ("मदद चाहिए, कोई जल्दी भेजो", "hi", "caller_request", "मदद चाहिए"),
        ("ભાઈ મદદ કરો", "gu", "caller_request", "ભાઈ મદદ કરો"),
        ("मला मदत हवी आहे", "mr", "caller_request", "मला मदत हवी आहे"),
        ("mujhe madad chahiye mera bhai behosh hai", "en", "caller_request", "mujhe madad chahiye"),
        ("mane madad joie chhe, ahi accident thayo chhe", "en", "caller_request", "mane madad joie chhe"),
        ("mala madat havi aahe, ek manus jakhmi aahe", "en", "caller_request", "mala madat havi aahe"),
        ("Highway pe accident, 5 people injured", "en", "road_accident", True),
        ("दो गाड़ियां आपस में भिड़ गई हैं", "hi", "road_accident", True),
        ("रेल की पटरी से ट्रेन उतर गई", "hi", "railway_incident", True),
        ("Train accident hua hai and many people are injured", "hi", "railway_incident", True),
        ("घर में आग नहीं लगी है", "hi", "fire_present", False),
        ("No one is injured and there is no fire", "en", "injuries_present", False),
        ("कोई बच्चा घायल नहीं है", "hi", "children_involved", False),
        ("Accident नहीं हुआ, सिर्फ car खराब हुई है", "hi", "emergency_type", "unknown"),
        ("अगर accident हो जाए तो क्या करना चाहिए?", "hi", "context_state", "hypothetical"),
        ("જો અકસ્માત થાય તો શું કરવું?", "gu", "context_state", "hypothetical"),
        ("What should I do if there is a fire?", "en", "context_state", "hypothetical"),
        ("कल accident हुआ था", "hi", "context_state", "historical"),
        ("Yesterday there was a fire", "en", "context_state", "historical"),
        ("Accident हुआ था लेकिन अब सब ठीक है", "hi", "context_state", "resolved"),
        ("Ambulance आ गई है, अब जरूरत नहीं है", "hi", "context_state", "resolved"),
        ("शायद 5 लोग घायल हैं", "hi", "context_state", "uncertain"),
        ("I think someone is injured", "en", "context_state", "uncertain"),
        ("2 ambulances चाहिए और 15 लोग घायल हैं", "hi", "victim_count", 15),
        ("around 25 people injured", "en", "victim_count", 25),
        ("सुमारे 25 लोग घायल", "hi", "victim_count_approximate", True),
        ("पहले 5 लोग घायल थे, अभी पता चला 8 लोग घायल हैं", "hi", "victim_count", 8),
        ("25 लोग घायल हैं, 25 लोग घायल हैं", "hi", "victim_count", 25),
        ("एक बच्चा घायल है, मदद भेजो", "hi", "children_involved", True),
        ("दो लोग अंदर फंस गए हैं", "hi", "trapped_persons", True),
        ("वो चाकू लेकर मेरे पीछे आ रहा है", "hi", "weapon_type", "knife"),
        ("मेरी मां सांस नहीं ले रही हैं, जल्दी ambulance भेजो", "hi", "medical_emergency", True),
        ("घर में धुआं भर गया है, आग दिख नहीं रही", "hi", "smoke_present", True),
        ("Fire drill चल रही है", "hi", "fire_present", False),
        ("Petrol pump ke paas accident hua", "en", "location_description", "Petrol pump"),
        ("रेलवे स्टेशन के सामने हादसा हुआ", "hi", "location_description", "रेलवे स्टेशन"),
    ],
)
def test_real_world_fact_extraction(text: str, language: str, field: str, expected: object) -> None:
    facts = extract_incident_facts(text, language)
    assert getattr(facts, field) == expected


def test_hypothetical_never_dispatches() -> None:
    facts = extract_incident_facts("अगर किसी को heart attack हो जाए तो क्या करें?", "hi")
    assert facts.current_emergency is False
    assert facts.hypothetical is True
    assert services_for_facts(facts) == []


def test_historical_railway_event_preserves_incident_but_not_dispatch() -> None:
    facts = extract_incident_facts("पिछले हफ्ते रेलवे स्टेशन पर हादसा हुआ था", "hi")
    assert facts.historical is True
    assert facts.railway_incident is True
    assert facts.current_emergency is False
    assert services_for_facts(facts) == []


def test_request_alone_does_not_invent_emergency_type() -> None:
    facts = extract_incident_facts("मदद चाहिए", "hi")
    assert facts.caller_request == "मदद चाहिए"
    assert facts.emergency_type == "unknown"
    assert facts.road_accident is False
    assert facts.medical_emergency is False


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("विद्यानगर में एक कॉलेज में कैंटीन में एलपीजी गैस ब्लास्ट हुआ है, मदद चाहिए।", "hi"),
        ("વિદ્યાનગરની કોલેજની કેન્ટીનમાં LPG ગેસનો બ્લાસ્ટ થયો છે, મદદ જોઈએ.", "gu"),
        ("विद्यानगरच्या कॉलेजच्या कॅन्टीनमध्ये एलपीजी गॅसचा स्फोट झाला आहे, मदत हवी आहे.", "mr"),
        ("There has been an LPG gas explosion in the college canteen, please send help.", "en"),
        ("College ni canteen ma LPG gas blast thayo che, help moklo.", "en"),
    ],
)
def test_lpg_gas_explosion_is_recognized_as_active_emergency(text: str, language: str) -> None:
    facts = extract_incident_facts(text, language)
    assert facts.current_emergency is True
    assert facts.explosion_present is True
    assert facts.emergency_type == "lpg"
    assert facts.sub_type in {"lpg_gas_explosion", "gas_leak", "fire_or_explosion", "lpg"}
    assert facts.location_description is not None
    assert "college" in facts.location_description.lower() or "कैंटीन" in facts.location_description or "કેન્ટીન" in facts.location_description or "canteen" in facts.location_description.lower()
    assert facts.caller_request is not None
    resolved = services_for_facts(facts)
    assert HelpRequired.FIRE_SERVICE in resolved
    assert HelpRequired.RESCUE in resolved


def test_explicit_injury_supports_medical_services_but_not_police() -> None:
    facts = extract_incident_facts("25 people injured, please send ambulance", "en")
    services = services_for_facts(facts)
    assert HelpRequired.AMBULANCE in services
    assert HelpRequired.MEDICAL_ASSISTANCE in services
    assert HelpRequired.POLICE not in services
