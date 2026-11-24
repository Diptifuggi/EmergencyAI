"""Deterministic incident fact extraction and service policy inputs.

The LLM may provide extraction hints, but these rules are authoritative for
classification and dispatch recommendations. They are decision support only;
a human dispatcher confirms every operational action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import re
import unicodedata
from typing import Literal

from .emergency_keywords import KEYWORDS, evidence
from .emergency_lexicon import lexicon_matches
from ..schemas.emergency_analysis import HelpRequired

_W = r"[\w\u0900-\u097F\u0A80-\u0AFF]"
_CLAUSE_BREAK = re.compile(
    r"[,.;!?।]|\b(?:and|but|ane|aur)\b|और|लेकिन|आणि|पण|અને|પણ",
    re.IGNORECASE,
)
_NEGATION_WORDS = (
    "not", "no", "never", "didn't", "did not", "wasn't", "was not",
    "without", "nobody", "no one", "नहीं", "नही", "कोई नहीं", "न कोई",
    "નથી", "નહીં", "નાહી", "નહીં", "નाही", "nahi", "nahin", "nathi",
)
_NON_LIVE_CONTEXT = (
    "movie", "story", "example", "joke", "training example",
    "yesterday", "last night", "last week", "last month", "earlier", "previously", "historically",
    "what should i do if", "if an accident happens", "if there is an accident",
    "જો અકસ્માત થાય તો", "જો અકસ્માત થાય તો શું કરવું", "જો આગ લાગે", "જો ગેસ લીક થાય",
    "જો આવું થાય", "ગઈકાલે", "ગઈ રાતે", "ગયા અઠવાડિયે", "થોડા દિવસ પહેલા",
    "जर असे झाले", "जर आग लागली", "जर गॅस गळला", "जर अपघात झाला",
    "काल", "काल रात्री", "गेल्या आठवड्यात", "काही दिवसांपूर्वी",
    "अगर accident हो जाए", "अगर आग लग जाए", "अगर गैस लीक हो जाए", "अगर किसी को", "अगर कोई",
    "कल", "कल रात", "पिछले हफ्ते", "पिछले महीने", "कुछ दिन पहले", "पहले हुआ था",
    "fire drill", "emergency drill", "practice drill",
)
_UNCERTAINTY_MARKERS = (
    "maybe", "perhaps", "i think", "i guess", "not sure", "possibly", "looks like", "seems like", "probably", "might be", "could be",
    "शायद", "हो सकता है", "लगता है", "मुझे ठीक से पता नहीं", "संभवतः", "पता नहीं",
    "કદાચ", "હોઈ શકે", "લાગે છે", "મને લાગે છે", "ખબર નથી", "શક્ય છે",
    "बहुधा", "कदाचित", "असू शकते", "असे वाटते", "मला वाटते", "माहित नाही", "शक्यता आहे", "exact count not confirmed",
    "exact count confirm nahi", "गिनती पक्की नहीं",
    "lagta hai", "shayad",
)
_POTENTIAL_RISK_MARKERS = (
    "risk of flooding", "risk of a flood", "possibility of flooding",
    "possibility of a flood", "may cause flooding", "could cause flooding",
    "flooding may occur", "flood may occur", "flood risk",
    "बाढ़ की संभावना", "बाढ़ आने की संभावना", "बाढ़ का खतरा",
    "बाढ़ आ सकती है", "बाढ़ आ सकता है",
    "પૂરની શક્યતા", "પૂર આવવાની શક્યતા", "પૂરનો ખતરો", "પૂર આવી શકે",
    "पुराची शक्यता", "पूर येण्याची शक्यता", "पुराचा धोका", "पूर येऊ शकतो",
)
_NEGATED_INCIDENT_MARKERS = (
    "no accident", "no fire", "no explosion", "nothing happened", "accident नहीं", "accident नहीं हुआ", "no fire", "fire नहीं", "आग नहीं", "आग नहीं लगी", "धमाका नहीं हुआ", "गैस लीक नहीं है", "कोई खतरा नहीं",
    "कोई accident नहीं", "गैस सिलेंडर नहीं फटा", "हादसा नहीं हुआ", "હાદસો નથી", "થયો નથી", "થયું નથી", "આગ લાગી નથી", "ગેસ લીક નથી", "કોઈ ખતરો નથી", "अपघात नाही", "नाही झाले", "झाले नाही", "आग लागली नाही", "गॅस गळती नाही", "धोका नाही",
)
_LPG_HINTS = (
    "lpg", "lpg gas", "gas leak", "gas leakage", "cylinder leak", "cooking gas",
    "smell gas", "gas blast", "gas explosion", "lpg blast", "lpg explosion",
    "एलपीजी", "गैस लीक", "गैस रिसाव", "सिलेंडर लीक", "गैस का ब्लास्ट",
    "गैस का विस्फोट", "ગેસ લીક", "ગેસ રિસાવ", "LPG ગેસ", "LPG",
    "गॅस गळती", "गॅसचा स्फोट", "गॅसचा ब्लास्ट", "એલપીજી",
)
_EXPLOSION_HINTS = (
    "explosion", "exploded", "blast", "bomb blast", "gas blast", "gas explosion",
    "विस्फोट", "स्फोट", "धमाका", "ब्लास्ट", "બ્લાસ્ટ", "ગેસનો બ્લાસ્ટ",
    "ગॅसचा स्फोट", "गॅसचा ब्लास्ट", "બ્લास्ट हुआ",
)
_EXPLOSION_HINTS += ("firecracker burst", "cracker burst")

_COUNT_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_DEVANAGARI_COUNT_WORDS = {
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5,
    "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14, "पंद्रह": 15,
    "पन्द्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18, "उन्नीस": 19,
    "बीस": 20, "इक्कीस": 21, "बाईस": 22, "तेईस": 23, "चौबीस": 24,
    "पच्चीस": 25, "पंचवीस": 25, "छब्बीस": 26, "सत्ताईस": 27, "अट्ठाईस": 28,
    "पंचवीस": 25,
    "उनतीस": 29, "तीस": 30, "चालीस": 40, "पचास": 50, "सौ": 100,
}
_GUJARATI_COUNT_WORDS = {
    "એક": 1, "બે": 2, "ત્રણ": 3, "ચાર": 4, "પાંચ": 5, "છ": 6,
    "સાત": 7, "આઠ": 8, "નવ": 9, "દસ": 10, "અગિયાર": 11,
    "બાર": 12, "તેર": 13, "ચૌદ": 14, "પંદર": 15, "વીસ": 20,
    "ત્રીસ": 30,
}
_MARATHI_COUNT_WORDS = {
    "एक": 1, "दोन": 2, "तीन": 3, "चार": 4, "पाच": 5, "सहा": 6,
    "सात": 7, "आठ": 8, "नऊ": 9, "दहा": 10, "अकरा": 11,
    "बारा": 12, "तेरा": 13, "चौदा": 14, "पंधरा": 15, "वीस": 20,
    "तीस": 30,
}
_PERSON_NOUNS = (
    "person", "people", "persons", "man", "men", "woman", "women", "boy",
    "girl", "girls", "child", "children", "kid", "kids", "baby", "babies", "patient",
    "passenger", "driver", "rider", "pedestrian", "worker", "student",
    "member", "victim", "injured", "casualty", "casualties", "family",
    "farmer", "farmers", "workers", "dada ji", "dadi", "nana", "nani",
    "parivar", "kisaan", "kisan", "ladkiyan", "ladke", "ladkiyon",
    "aadmi", "aurat", "pati", "patni", "buzurg", "bhai", "brother",
    "भाई", "भाऊ", "भावाला", "દાદી", "દાદા", "તે", "वह", "वो",
    "માણસને", "માણસ", "माणसाला", "ती", "तो", "त्याला", "आजी",
    "चालक", "ડ્રાઈવર", "મજૂર", "मजूर",
    "आदमी", "व्यक्ति", "महिला", "लड़का", "लड़की", "बच्चा", "बच्चे", "मरीज",
    "इंसान", "लोग", "लोक", "माणूस", "व्यक्ती", "मुलगा", "मुलगी", "रुग्ण",
    "માણસ", "વ્યક્તિ", "સ્ત્રી", "છોકરો", "બાળક", "દર્દી", "લોકો",
    "aadmi", "ladka", "ladki", "bachcha", "log",
)
_VEHICLE_NOUNS = (
    "car", "bike", "motorcycle", "scooter", "auto", "rickshaw", "e-rickshaw",
    "tempo", "tractor", "bus", "truck", "lorry", "tanker", "dumper", "cycle",
    "vehicle", "gaadi", "गाड़ी", "ट्रक", "कार", "बाइक", "गाडी", "ગાડી",
    "બાઇક", "બાઈક", "કાર",
)
_COLLISION_TERMS = (
    "hit", "ran over", "run over", "knocked down", "rammed", "dashed", "skidded",
    "slipped", "overturned", "fell off", "fell into", "crashed", "collided", "takkar",
    "gir", "palat", "phisal", "घसर", "फिसल", "कुचल", "उड़ा", "टक्कर",
    "ટક્કર", "ધડક", "धडक", "અથડ",
)
# Approximate group sizes are research assumptions, not measured victim counts.
RESEARCH_ASSUMPTION_VICTIM_COUNTS = {"plural": 2, "many": 5, "dozens": 24}

_PHRASES: dict[str, tuple[str, ...]] = {
    "home_intrusion": (
        "breaking into my house", "breaking into my home", "broke into my house",
        "broke into my home", "home intrusion", "house break-in", "home break-in",
        "intruder in my house", "intruder in my home", "someone is inside my house",
        "someone is inside my home", "someone entered my house", "someone entered my home",
        "stranger inside my house", "stranger inside my home",
        "mere ghar mein koi ghus raha", "koi ghar mein ghus raha",
    ),
    "burglary": ("burglary", "burglar", "burglars", "breaking in", "break-in"),
    "robbery": ("robbery", "robbery in progress", "robber", "robbers", "someone is robbing me", "stealing right now", "someone is stealing", "chain snatching", "chain snatched", "snatched my chain", "snatched my gold chain", "chain cheen li"),
    "kidnapping": ("kidnapped", "kidnapping", "abducted", "kidnap kar liya", "kidnap kar li"),
    "crime": ("crime happening", "crime in progress", "criminal", "thief", "thieves", "theft happening"),
    "police_request": ("police help", "need police", "send police", "police immediately", "police assistance", "police assistant"),
    "active": ("right now", "currently", "happening now", "at this moment", "just now", "abhi", "just snatched", "snatched my chain", "snatched my gold chain", "abhi kisi ne", "breaking in", "attacking me", "chasing me", "stealing right now", "following me", "being followed", "peecha kar raha", "peecha kar rahi", "shots fired", "firing shots"),
    "violence": ("attack", "attacked", "attacking me", "assault", "being assaulted", "fight", "violent person", "threatening me", "shooting", "firing shots", "shots fired", "stabbing", "stabbed", "acid attack", "acid thrown", "acid was thrown", "tezaab phenk diya", "goliyan chala", "goli chala"),
    "weapon": ("gun", "pistol", "rifle", "knife", "weapon", "armed", "firearm", "holding a gun", "threatening me with a knife", "firing shots", "bandook se goliyan", "bandook se goli"),
    "gun": ("gun", "pistol", "rifle", "firearm"),
    "domestic": ("domestic violence", "my husband is beating me", "my wife is attacking me", "partner is hitting me", "family member is threatening me", "my husband is threatening me", "mera pati mujhe maar raha", "pati mujhe maar raha", "pati mujhe maar raha hai"),
    "sexual": ("sexual assault", "sexually assaulted", "rape", "molestation", "molested", "balatkar ho raha", "aurat ke saath balatkar", "yaun hamla"),
    "stalking": ("stalking", "following me", "being followed", "following her", "mera peecha kar raha", "mera peecha kar rahi", "peecha kar raha", "peecha kar rahi"),
    "harassment": ("harassment", "eve teasing", "teasing girls", "boys teasing girls", "ladke ladkiyon ko chhed"),
    "reckless_driving": ("reckless driving", "driving dangerously", "dangerous driving", "drunk driver", "rash driving", "khatarnaak tarike se gaadi chala", "khatarnak tarike se gaadi chala", "sharabi driver"),
    "security_threat": ("bomb threat", "bomb ki dhamki", "bomb threat at"),
    "child_abuse": ("child is being beaten", "a child is being beaten", "child abuse", "bachche ko maara ja raha"),
    "riot": ("riot", "mob is fighting", "throwing stones", "patthar phenk"),
    "chain_snatching": ("chain snatching", "chain snatched"),
    "vehicle_trapped": ("driver trapped", "trapped in cabin", "trapped in the cabin", "driver is trapped in the cabin", "trapped in vehicle", "trapped inside car", "trapped inside truck", "truck ka driver cabin mein fansa", "ड्राइवर केबिन में फंसा", "ડ્રાઈવર કેબિનમાં ફસાયો", "ट्रकचा चालक केबिनमध्ये अडकला"),
    "child": ("my child", "my son", "my daughter", "child is missing", "child is trapped", "kidnapped my child", "child is injured", "child is in danger", "child is being beaten", "a child is being beaten", "child lost", "my child is lost", "bachcha", "bachche", "બાળક", "મૂલ", "मूल", "बच्चा", "बच्चे", "bachche ko maara", "bachche ko kidnap", "bachcha kho gaya", "bachcha bazaar mein kho gaya"),
    "elderly": ("elderly", "senior citizen", "old person", "old people", "elderly people", "grandfather", "grandmother", "dada ji", "dadi", "आजी", "दादी", "દાદી", "બુજર્ગ", "bujurg", "buzurg", "બુઝુર્ગ", "बुजुर्ग", "वृद्ध"),
    "missing": ("child is missing", "my child is missing", "my child is lost", "child lost", "missing person", "cannot find my child", "went missing", "gum ho gaye", "bachcha kho gaya", "bachcha bazaar mein kho gaya", "bazaar mein kho gaya", "dada ji gum ho gaye"),
    "smoke": ("smoke everywhere", "smoke in", "heavy smoke"),
    "distress": ("scared", "afraid", "frightened", "save me"),
}


@lru_cache(maxsize=4096)
def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    words = re.escape(phrase).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!{_W}){words}(?!{_W})", re.IGNORECASE)


def _is_negated_clause(clause: str, start: int, end: int) -> bool:
    before = clause[:start]
    after = clause[end:]
    return any(
        _phrase_pattern(marker).search(before[-48:])
        or _phrase_pattern(marker).search(after[:32])
        for marker in _NEGATION_WORDS
    )


def _contains(text: str, phrases: tuple[str, ...]) -> bool:
    for clause in _CLAUSE_BREAK.split(text):
        for phrase in phrases:
            for match in _phrase_pattern(phrase).finditer(clause):
                if not _is_negated_clause(clause, match.start(), match.end()):
                    return True
    return False


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(
        _phrase_pattern(phrase).search(clause)
        for clause in _CLAUSE_BREAK.split(text)
        for phrase in phrases
    )


def _has_vehicle_collision(text: str) -> bool:
    return _contains(text, _VEHICLE_NOUNS) and _contains(text, _COLLISION_TERMS)


@dataclass(frozen=True)
class EvidenceItem:
    concept: str
    value: object
    source_text: str
    certainty: str


@dataclass(frozen=True)
class IncidentFacts:
    emergency_type: str
    sub_type: str | None
    non_live_context: bool
    context_state: str
    current_emergency: bool
    hypothetical: bool
    historical: bool
    resolved: bool
    immediate_danger: bool
    crime_in_progress: bool
    police_required: bool
    medical_emergency: bool
    injuries_present: bool
    severe_bleeding: bool
    unconscious_person: bool
    fire_present: bool
    smoke_present: bool
    explosion_present: bool
    rescue_required: bool
    trapped_persons: bool
    weapon_present: bool
    weapon_type: str | None
    victim_count: int | None
    victim_count_approximate: bool
    victim_count_source: Literal["explicit", "default", "plural_estimate", "none"]
    uncertain: bool
    negated: bool
    children_involved: bool
    elderly_involved: bool
    domestic_violence: bool
    sexual_violence: bool
    missing_person: bool
    burglary_in_progress: bool
    home_intrusion: bool
    robbery_in_progress: bool
    assault_in_progress: bool
    road_accident: bool
    highway_incident: bool
    railway_incident: bool
    cyber_crime: bool
    lpg_leak: bool
    heavy_rain: bool
    flood_risk: bool
    flood_confirmed: bool
    caller_request: str | None
    location_description: str | None
    emergency_keywords: list[str] = field(default_factory=list)
    evidence: tuple[EvidenceItem, ...] = ()


def services_for_facts(facts: IncidentFacts) -> list[HelpRequired]:
    """Derive services only from explicit incident evidence."""
    if not facts.current_emergency:
        if facts.emergency_type == "unknown" and facts.context_state == "non_live":
            return [HelpRequired.UNKNOWN]
        return []
    services: list[HelpRequired] = []
    if facts.police_required or facts.road_accident or facts.railway_incident:
        services.append(HelpRequired.POLICE)
    if (
        facts.railway_incident
        or (facts.medical_emergency and facts.sub_type != "minor_illness")
        or (facts.road_accident and facts.injuries_present)
    ):
        services.append(HelpRequired.AMBULANCE)
    if facts.injuries_present or facts.severe_bleeding:
        services.extend([HelpRequired.AMBULANCE, HelpRequired.MEDICAL_ASSISTANCE])
    elif facts.medical_emergency:
        services.append(HelpRequired.MEDICAL_ASSISTANCE)
    if facts.emergency_type == "assault" or (
        facts.emergency_type == "women_safety" and facts.sexual_violence
    ):
        services.append(HelpRequired.AMBULANCE)
    if facts.fire_present or facts.explosion_present or facts.smoke_present:
        services.append(HelpRequired.FIRE_SERVICE)
    if facts.road_accident and (facts.fire_present or facts.explosion_present):
        services.append(HelpRequired.AMBULANCE)
    if facts.explosion_present and facts.injuries_present:
        services.append(HelpRequired.AMBULANCE)
    # Active explosions justify fire/rescue readiness, but this policy does
    # not turn that operational recommendation into a trapped-person fact.
    if facts.explosion_present and facts.lpg_leak:
        services.extend([HelpRequired.RESCUE, HelpRequired.AMBULANCE])
    if facts.rescue_required or facts.trapped_persons:
        services.append(HelpRequired.RESCUE)
        if facts.railway_incident:
            services.append(HelpRequired.AMBULANCE)
        elif facts.emergency_type == "disaster" and (
            facts.flood_confirmed or facts.sub_type == "crowd_emergency"
        ):
            services.append(HelpRequired.AMBULANCE)
        else:
            services.extend([HelpRequired.FIRE_SERVICE, HelpRequired.AMBULANCE])
    if facts.emergency_type == "disaster" and not facts.trapped_persons and not services:
        services.append(HelpRequired.MULTIPLE_SERVICES)
    if facts.domestic_violence:
        services.append(HelpRequired.WOMEN_SAFETY_SUPPORT)
    if facts.emergency_type in {"women_safety", "harassment"}:
        services.append(HelpRequired.WOMEN_SAFETY_SUPPORT)
    if facts.children_involved:
        services.append(HelpRequired.CHILD_PROTECTION)
    if facts.cyber_crime:
        services.append(HelpRequired.CYBERCRIME)
    if facts.lpg_leak:
        services.append(HelpRequired.LPG)
    if not services:
        return [HelpRequired.UNKNOWN]
    return list(dict.fromkeys(services))


def extract_incident_facts(text: str, language: str = "en") -> IncidentFacts:
    normalized = " ".join(text.casefold().split())
    empty_or_noise = not normalized.strip(" .!?।")
    drill = _contains_any(normalized, ("fire drill", "emergency drill", "practice drill"))
    non_emergency_query = empty_or_noise or _contains_any(normalized, (
        "this is a test call", "test call", "prank",
        "what is the fire brigade number", "what is fire brigade number",
        "fire brigade number", "fire brigade ka number",
        "fire brigade ka number kya hai",
    ))
    hypothetical = _contains_any(normalized, (
        "what should i do if", "if an accident happens", "if there is an accident",
        "what if", "suppose", "supposing", "in case", "if this happens",
        "જો અકસ્માત થાય તો", "જો આગ લાગે", "જો ગેસ લીક થાય", "જો સિલિન્ડર ફાટે", "જો આવું થાય",
        "जर असे झाले", "जर आग लागली", "जर गॅस गळला", "जर अपघात झाला",
        "अगर ट्रेन हादसा हो जाए", "अगर हादसा हो", "अगर accident हो जाए", "अगर आग लग जाए", "अगर गैस लीक हो जाए", "अगर गैस सिलेंडर फट जाए",
        "अगर किसी को", "अगर कोई", "if there is a fire",
        "agar aag lag jaye", "agar aag lage", "agar aag lagti hai",
    )) or drill
    historical = _contains_any(normalized, (
        "yesterday", "last night", "last week", "last month", "earlier", "previously", "historically", "कल", "कल रात", "पिछले हफ्ते", "पिछले महीने", "कुछ दिन पहले", "हुआ था", "गई थी", "गया था", "ગઈકાલે", "ગઈ રાતે", "ગયા અઠવાડિયે", "થયું હતું", "झाले होते", "काल", "काल रात्री", "गेल्या आठवड्यात", "kal",
    ))
    resolved = _contains_any(normalized, (
        "now everything is fine", "now all is well", "now it is controlled", "ambulance has arrived", "police already reached", "everything is fine now", "situation is under control", "fire is out", "person is safe", "no longer dangerous", "problem resolved", "emergency is over", "everyone is safe",
        "अब सब ठीक", "अब सब सुरक्षित", "स्थिति नियंत्रण में", "आग बुझ गई", "आग पर काबू पा लिया", "अब जरूरत नहीं", "अब खतरा नहीं", "समस्या हल हो गई", "इमरजेंसी खत्म हो गई", "सब सुरक्षित", "पुलिस पहुंच गई",
        "હવે બધું ઠીક", "હવે બધા સુરક્ષિત", "પરિસ્થિતિ કાબૂમાં", "આગ બુઝાઈ ગઈ", "હવે ખતરો નથી", "સમસ્યા ઉકેલાઈ ગઈ", "ઇમરજન્સી પૂરી થઈ",
        "आता सर्व ठीक", "आता सगळे सुरक्षित", "परिस्थिती नियंत्रणात", "आग विझली", "आग आटोक्यात", "आता धोका नाही", "समस्या सुटली", "आणीबाणी संपली",
        "aag bujh gayi", "sab surakshit", "sab theek",
    ))
    potential_risk = _contains_any(normalized, _POTENTIAL_RISK_MARKERS)
    uncertain = _contains_any(normalized, _UNCERTAINTY_MARKERS)
    negation_marker = _contains_any(normalized, _NEGATED_INCIDENT_MARKERS)
    flags = evidence(text, language)
    hit = {name: _contains(normalized, phrases) for name, phrases in _PHRASES.items()}
    if hypothetical or non_emergency_query:
        hit = {name: False for name in hit}
        flags = {name: False for name in flags}
    affirmed_incident = any(flags.get(name) for name in (
        "accident", "injury", "bleeding", "unconscious", "medical", "fire",
        "smoke", "explosion", "trapped", "railway", "road", "police", "lpg",
        "cybercrime", "child_missing",
    )) or any(hit.get(name) for name in (
        "crime", "burglary", "robbery", "violence", "domestic", "sexual",
        "missing", "smoke", "vehicle_trapped", "harassment", "stalking",
        "reckless_driving", "security_threat", "child_abuse", "riot",
    ))
    negated = negation_marker and not affirmed_incident
    contextual = (
        hypothetical or historical or resolved or uncertain or negated or non_emergency_query
        or potential_risk or _contains_any(normalized, _NON_LIVE_CONTEXT)
    )

    domains = lexicon_matches(text, language)
    if hypothetical or non_emergency_query or uncertain or negated:
        domains = {}

    medical = bool(flags.get("medical"))
    injury = bool(flags.get("injury") or flags.get("bleeding") or flags.get("unconscious"))
    lpg = bool(flags.get("lpg") or any(marker in normalized for marker in _LPG_HINTS))
    explosion = bool(flags.get("explosion") or any(marker in normalized for marker in _EXPLOSION_HINTS))
    fire = bool(flags.get("fire"))
    trapped = bool(
        "rescue" in domains
        or "structural_collapse" in domains
        or "drowning" in domains
        or hit["vehicle_trapped"]
    )
    railway_context = bool(flags.get("railway"))
    railway_derailment = railway_context and _contains(
        normalized, (
            "derailment", "derailed", "पटरी से उतर", "पटरी से ट्रेन उतर",
            "પાટા પરથી ઉતરી", "રुळावरून घસર", "train patri se utar",
        )
    )
    accident_evidence = bool(flags.get("accident"))
    railway_rescue = railway_context and _contains(
        normalized, (
            "person hit by train", "hit by train", "train hit someone",
            "train की चपेट", "train se kat", "train se kat gaya",
        )
    )
    railway = railway_context and bool(
        accident_evidence or railway_derailment or railway_rescue
        or _contains(normalized, ("train accident", "railway accident", "train crash", "train collision"))
    )
    cylinder_blast = _contains(
        normalized, ("cylinder blast", "cylinder exploded", "cylinder phat", "silinder phat")
    )
    lpg = lpg or cylinder_blast
    explosion = explosion or cylinder_blast
    road = bool(
        flags.get("road")
        or (flags.get("highway") and (accident_evidence or _contains_any(normalized, _VEHICLE_NOUNS)))
        or hit["vehicle_trapped"]
        or _has_vehicle_collision(normalized)
        or (accident_evidence and not railway)
    )
    if road and _contains(
        normalized, (
            "pedestrian", "hit a man", "hit a woman", "hit by", "ran over",
            "run over", "knocked down", "takkar maar", "takra", "gaadi ne",
        )
    ) and not flags.get("no_injury"):
        injury = True
    if road and _contains(normalized, _COLLISION_TERMS) and _contains(
        normalized, _PERSON_NOUNS
    ) and not flags.get("no_injury"):
        injury = True
    if road and _contains(
        normalized, (
            "inside", "andar", "अंदर", "અંદર", "आत", "trapped", "फंसा",
            "फंसे", "ફસાયો", "ફસાયેલા", "अडकला", "अडकले", "fansa", "fanse",
        )
    ):
        trapped = True
    highway = bool(
        flags.get("highway")
        or _contains(normalized, ("highway", "हाईवे", "राजमार्ग", "હાઈવે", "ધોરીમાર્ગ", "महामार्ग"))
    )
    cyber = bool(flags.get("cybercrime"))
    drowning = "drowning" in domains
    structural_collapse = "structural_collapse" in domains
    borewell_rescue = _contains_any(normalized, ("borewell", "bore well", "borehole"))
    elevator_rescue = _contains(
        normalized, ("stuck in the lift", "stuck in a lift", "stuck in elevator", "lift mein fans", "lift mein phans")
    )
    natural_disaster = "natural_disaster" in domains
    heavy_rain = any(term in normalized for term in (
        "heavy rain", "बहुत भारी बारिश", "भारी बारिश", "મુશળધાર વરસાદ",
        "બહુ જ ભારે વરસાદ", "મુસળધાર પाऊस", "मुसळधार पाऊस",
    ))
    flood_risk = potential_risk and any(term in normalized for term in (
        "flood", "flooding", "बाढ़", "પૂર", "पूर",
    ))
    flood_confirmed = any(term in normalized for term in (
        "flooding", "flood water", "flood water is entering", "floodwater entering",
        "flood came", "flood has come", "flood aa gaya", "baadh ka paani",
        "बाढ़ आ गई", "बाढ़ आई", "पानी भर गया", "ઘરોમાં પાણી ઘૂસી ગયું",
        "પૂર આવ્યું", "पूर आला", "पूर आला आहे",
    )) and not (hypothetical or negated or potential_risk)
    electrical_incident = "electrical" in domains
    hazmat_incident = "chemical_hazmat" in domains
    animal_attack = "animal_attack" in domains
    crowd_emergency = "crowd_emergency" in domains
    self_harm_crisis = "self_harm_crisis" in domains
    medical = medical or drowning or animal_attack or self_harm_crisis
    minor_illness = medical and _contains(
        normalized, (
            "fever", "vomiting", "bukhar", "ulti", "बुखार", "उल्टी",
            "તાવ", "ઉલટી", "ताप", "उलटी",
        )
    ) and not _contains(
        normalized, (
            "poison", "phenyl", "zehar", "जहर", "ઝેર", "विष",
            "फिनाइल", "ફિનાઇલ", "फिनाइल प्यायले",
            "blood", "bleeding", "ખૂન", "रक्त", "unconscious",
        )
    )
    injury = injury or animal_attack or crowd_emergency
    # A flood, storm, crowd, or other disaster is not evidence that somebody
    # is trapped.  Entrapment/rescue requires explicit language (or drowning,
    # collapse, which inherently describes a person in immediate danger).
    trapped = trapped or drowning or structural_collapse
    chain_snatching = _contains(
        normalized, ("chain snatching", "chain snatched", "snatched my chain", "snatched my gold chain", "chain cheen li")
    )
    stalking = _contains_any(normalized, ("stalking", "following me", "being followed", "following her", "peecha kar raha", "peecha kar rahi"))
    harassment = hit["harassment"] or _contains_any(normalized, ("harassment", "eve teasing", "teasing girls"))
    reckless_driving = hit["reckless_driving"]
    security_threat = hit["security_threat"]
    child_abuse = hit["child_abuse"]
    riot = hit["riot"]
    sexual = hit["sexual"] or _contains_any(normalized, ("molestation", "sexual assault", "molested"))
    active_crime = bool(
        hit["active"] and (
            hit["crime"] or hit["burglary"] or hit["robbery"] or hit["violence"]
            or hit["home_intrusion"] or chain_snatching or harassment or stalking or sexual
            or hit["kidnapping"]
        )
    )
    home = hit["home_intrusion"] or (hit["burglary"] and ("house" in normalized or "home" in normalized))
    burglary = bool(home and (hit["burglary"] or hit["home_intrusion"]))
    robbery = bool((hit["robbery"] or chain_snatching) and (active_crime or hit["active"]))
    assault = _contains(
        normalized,
        (
                "attack", "attacked", "attacking", "assault", "being assaulted", "fight",
                "shooting", "firing shots", "shots fired", "stabbing", "stabbed",
                "acid attack", "acid thrown", "acid was thrown", "tezaab phenk diya",
                "goliyan chala", "goli chala",
        ),
    )
    weapon = bool(hit["weapon"] or flags.get("weapon"))
    children_involved = bool(
        hit["child"] or flags.get("child") or flags.get("child_missing")
    )
    cyber_police_required = cyber and _contains_any(
        normalized, ("otp fraud", "otp scam", "blackmail", "morphed photos")
    )
    police = bool(
        hit["police_request"] or hit["crime"] or hit["burglary"] or hit["robbery"]
        or hit["violence"]
        or (flags.get("police") and (not cyber or cyber_police_required))
        or hit["domestic"]
        or hit["missing"] or weapon or crowd_emergency or road or railway
        or chain_snatching or harassment or stalking or sexual or structural_collapse
        or hit["kidnapping"] or self_harm_crisis or reckless_driving
        or security_threat or child_abuse or riot or cyber_police_required
    )
    immediate = bool(
        active_crime or weapon or hit["domestic"] or hit["missing"] or drowning
        or structural_collapse or crowd_emergency or self_harm_crisis
        or child_abuse or security_threat or reckless_driving or riot
        or (flags.get("immediate") and (police or medical or fire))
    )
    fire = fire or bool(
        flags.get("fire") or hazmat_incident
        or (electrical_incident and _contains_any(normalized, ("fire", "spark", "sparks")))
    )
    hot_liquid_burn = _contains(
        normalized, (
            "burned by boiling oil", "burnt by boiling oil", "boiling oil",
            "garam tel se jal", "garm tel se jal", "गरम तेल से जल",
            "उबलते तेल से जल", "ઉકળતા તેલથી દાઝી",
            "ગરમ તેલથી દાઝી", "उकळत्या तेलाने भाजली",
        )
    )
    explicit_fire = _contains(
        normalized, ("fire", "flames", "आग लग", "આગ લાગી", "आग लागली")
    )
    if hot_liquid_burn and not explicit_fire:
        fire = False
    trapped = trapped or borewell_rescue or elevator_rescue or bool(
        fire and _contains(normalized, (
            "family inside", "family is trapped inside", "workers inside",
            "workers are stuck inside", "people inside", "person trapped",
            "parivar andar fansa", "परिवार अंदर फंसा", "પરિવાર અંદર ફસાયેલો",
            "કુટુંબ અંદર ફસાયેલું", "कुटुंब आत अडकले", "mazdoor andar fanse",
            "लोग अंदर फंसे", "કામદારો અંદર ફસાયા",
        ))
    )
    flood_rescue = flood_confirmed and _contains(
        normalized, (
            "old people inside", "old people are inside", "elderly inside",
            "elderly are inside", "बुजुर्ग अंदर", "वृद्ध अंदर",
            "bujurg andar", "buzurg andar",
        )
    )
    rescue_required = (
        trapped or railway_derailment or railway_rescue or flood_rescue
        or crowd_emergency or elevator_rescue
    )
    location_description = (
        None if self_harm_crisis else _extract_location(text, railway)
    )

    if empty_or_noise:
        kind, subtype = "unknown", None
    elif non_emergency_query:
        kind, subtype = "other", None
    elif hypothetical:
        kind, subtype = "unknown", None
    elif cyber:
        kind, subtype = "cybercrime", "online_fraud"
    elif lpg and (explosion or "gas leak" in normalized or "gas leakage" in normalized):
        kind, subtype = "lpg", "lpg_gas_explosion" if explosion else "gas_leak"
    elif lpg:
        kind, subtype = "lpg", "gas_leak"
    elif borewell_rescue:
        kind, subtype = "disaster", "borewell_rescue"
    elif structural_collapse:
        kind, subtype = "disaster", "structural_collapse"
    elif natural_disaster:
        kind, subtype = "disaster", "natural_disaster"
    elif drowning:
        kind, subtype = "medical", "drowning"
    elif hazmat_incident:
        kind, subtype = "disaster", "chemical_hazmat"
    elif fire and electrical_incident:
        kind, subtype = "fire", "electrical"
    elif electrical_incident:
        kind, subtype = "medical", "electrical_emergency"
    elif animal_attack:
        kind, subtype = "medical", "animal_attack"
    elif crowd_emergency:
        kind, subtype = "disaster", "crowd_emergency"
    elif self_harm_crisis:
        kind, subtype = "medical", "self_harm_crisis"
    elif security_threat:
        kind, subtype = "police", "security_threat"
    elif reckless_driving:
        kind, subtype = "police", "reckless_driving"
    elif riot:
        kind, subtype = "police", "riot"
    elif child_abuse:
        kind, subtype = "child_safety", "child_abuse"
    elif elevator_rescue:
        kind, subtype = "disaster", "rescue"
    elif children_involved and injury:
        kind, subtype = "child_safety", "injured_child"
    elif road or railway or accident_evidence:
        hit_and_run = bool(flags.get("hit_and_run")) or _contains_any(
            normalized, (
                "hit and run", "ran away", "bhaag gaya", "bhaag gayi",
                "भाग गया", "भाग गई", "ભાગી ગઈ", "पळून गेली", "पळून गेला",
            )
        )
        kind, subtype = (
            "accident",
            "hit_and_run" if hit_and_run else
            "railway_accident" if railway else "road_accident" if road else "unknown_accident",
        )
    elif fire or explosion or hit["smoke"] or flags.get("smoke"):
        subtype = (
            "wildfire" if _contains_any(normalized, ("forest fire", "wildfire", "crop fire", "grass fire"))
            else "industrial" if _contains_any(normalized, ("factory", "industrial"))
            else "fire_or_explosion" if fire else "suspected_fire"
        )
        kind = "fire"
    elif medical:
        kind, subtype = "medical", "minor_illness" if minor_illness else "medical_emergency"
    elif hit["kidnapping"]:
        kind, subtype = "child_safety", "kidnapping"
    elif hit["missing"] and children_involved:
        kind, subtype = "child_safety", "missing_child"
    elif hit["missing"]:
        kind, subtype = "police", "missing_person"
    elif sexual or stalking:
        kind, subtype = "women_safety", "sexual_assault" if sexual else "stalking"
    elif hit["domestic"] or flags.get("domestic_violence"):
        kind, subtype = "domestic_violence", "domestic_violence"
    elif robbery:
        kind, subtype = "robbery", "chain_snatching" if chain_snatching else "robbery_in_progress"
    elif assault:
        kind, subtype = "assault", (
            "acid_attack" if _contains_any(normalized, ("acid attack", "acid thrown", "acid was thrown"))
            else "shooting" if _contains_any(normalized, ("shooting", "shots fired"))
            else "stabbing" if _contains_any(normalized, ("stabbing", "stabbed"))
            else "assault"
        )
    elif harassment:
        kind, subtype = "harassment", "eve_teasing" if _contains_any(normalized, ("eve teasing", "teasing girls")) else "harassment"
    elif police and (active_crime or weapon or hit["domestic"]):
        kind, subtype = "crime_police", "burglary_home_intrusion" if burglary else "active_crime"
    elif police:
        kind, subtype = "police", "police_assistance"
    else:
        kind, subtype = "unknown", None

    keyword_candidates = [
        phrase for name, phrases in _PHRASES.items()
        if hit.get(name) for phrase in phrases if phrase in normalized
    ]
    for category, phrases in KEYWORDS.get(language, {}).items():
        if category in {"no_injury", "major", "immediate"}:
            continue
        keyword_candidates.extend(
            phrase for phrase in phrases if phrase.casefold() in normalized
        )
    keyword_candidates.extend(
        phrase
        for matched_phrases in domains.values()
        for phrase in matched_phrases
    )
    if flags.get("medical"):
        keyword_candidates.extend(phrase for phrase in ("chest pain", "difficulty breathing", "ambulance") if phrase in normalized)
    if self_harm_crisis:
        keyword_candidates = ["self_harm_crisis"]
    keywords = list(dict.fromkeys(keyword_candidates))[:20]
    victim_count, victim_count_approximate, victim_count_source = _extract_victim_count(normalized)
    if not contextual and victim_count is None and (kind != "unknown" or immediate):
        victim_count, victim_count_source = 1, "default"
    if contextual:
        victim_count, victim_count_approximate, victim_count_source = None, False, "none"
    caller_request = _extract_caller_request(normalized)
    if not caller_request and "help" in normalized:
        caller_request = "help"

    certainty = (
        "possible" if potential_risk or uncertain
        else "historical" if historical
        else "resolved" if resolved
        else "confirmed"
    )
    evidence_items: list[EvidenceItem] = []
    if heavy_rain:
        evidence_items.append(EvidenceItem("heavy_rain", True, text, "confirmed"))
    if flood_risk:
        evidence_items.append(EvidenceItem("flood", True, text, "possible"))
    if flood_confirmed:
        evidence_items.append(EvidenceItem("flood", True, text, certainty))
    if explosion:
        evidence_items.append(EvidenceItem("explosion", True, text, certainty))
    if lpg:
        evidence_items.append(EvidenceItem("lpg", True, text, certainty))
    if caller_request:
        evidence_items.append(EvidenceItem("caller_request", caller_request, text, "confirmed"))
    if victim_count is not None:
        evidence_items.append(EvidenceItem("victim_count", victim_count, text, certainty))

    return IncidentFacts(
        emergency_type=kind,
        sub_type=subtype,
        non_live_context=contextual,
        context_state=("hypothetical" if hypothetical else "resolved" if resolved else "historical" if historical else "potential_risk" if potential_risk else "uncertain" if uncertain else "negated" if negated else "non_live" if non_emergency_query else "current"),
        current_emergency=not contextual,
        hypothetical=hypothetical,
        historical=historical,
        resolved=resolved,
        uncertain=uncertain,
        negated=negated,
        immediate_danger=immediate,
        crime_in_progress=active_crime,
        police_required=police,
        medical_emergency=medical,
        injuries_present=injury,
        severe_bleeding=bool(flags.get("bleeding")),
        unconscious_person=bool(flags.get("unconscious")),
        fire_present=fire,
        smoke_present=bool(hit["smoke"] or flags.get("smoke")),
        explosion_present=explosion,
        rescue_required=rescue_required,
        trapped_persons=trapped,
        weapon_present=weapon,
        weapon_type=(
            "gun" if hit["gun"] or "बंदूक" in normalized else
            "knife" if "knife" in normalized or "चाकू" in normalized else None
        ),
        victim_count=victim_count,
        victim_count_approximate=victim_count_approximate,
        victim_count_source=victim_count_source,
        children_involved=children_involved,
        elderly_involved=bool(hit["elderly"] or flags.get("elderly")),
        domestic_violence=hit["domestic"] or bool(flags.get("domestic_violence")),
        sexual_violence=sexual,
        missing_person=hit["missing"],
        burglary_in_progress=burglary,
        home_intrusion=home,
        robbery_in_progress=robbery,
        assault_in_progress=assault,
        road_accident=road,
        highway_incident=highway,
        railway_incident=railway,
        cyber_crime=cyber,
        lpg_leak=lpg,
        heavy_rain=heavy_rain,
        flood_risk=flood_risk,
        flood_confirmed=flood_confirmed,
        caller_request=caller_request,
        location_description=location_description,
        emergency_keywords=keywords,
        evidence=tuple(evidence_items),
    )


def _extract_victim_count(text: str) -> tuple[int | None, bool, str]:
    """Extract a stated count or an explicitly labeled research estimate."""
    if _contains_any(text, (
        "nobody injured", "nobody is injured", "no one injured", "no one is injured",
        "no injuries", "कोई घायल नहीं", "कोई चोट नहीं", "કોઈ ઘાયલ નથી",
        "किसी को चोट नहीं आई",
        "कोणी जखमी नाही", "કોઈને ઈજા થઈ નથી", "કોઈ ઘાયલ નથી",
        "कोणालाही दुखापत नाही", "कोणी जखमी नाही",
        "kisi ko chot nahi aayi", "koi ghayal nahi", "koi chot nahi",
        "कोणालाही दुखापत झाली नाही",
    )):
        return 0, False, "explicit"

    count_words = {
        **_COUNT_WORDS,
        **_DEVANAGARI_COUNT_WORDS,
        **_GUJARATI_COUNT_WORDS,
        **_MARATHI_COUNT_WORDS,
        "ek": 1, "do": 2, "teen": 3, "char": 4, "panch": 5,
    }
    nouns = "|".join(
        sorted((re.escape(noun) for noun in _PERSON_NOUNS), key=len, reverse=True)
    )
    person_after_count = re.compile(rf"^\s+(?:of\s+)?(?:{nouns})(?!{_W})", re.IGNORECASE)
    family_pattern = re.compile(
        rf"(?<!{_W})(?:a\s+)?family\s+of\s+(?P<count>\d{{1,3}}|"
        rf"{'|'.join(sorted((re.escape(word) for word in count_words), key=len, reverse=True))})(?!{_W})",
        re.IGNORECASE,
    )
    matches: list[tuple[int, str, int, bool]] = []
    number_patterns = [
        (_phrase_pattern(token), token, value) for token, value in count_words.items()
    ]
    number_patterns.extend([
        (re.compile(rf"(?<!{_W})\d{{1,3}}(?!{_W})"), "", -1),
        (_phrase_pattern("both"), "both", 2),
        (_phrase_pattern("couple of"), "couple of", 2),
    ])
    for number_pattern, token, numeric_value in number_patterns:
        for match in number_pattern.finditer(text):
            suffix = text[match.end():]
            is_crime_actor = token in {"a", "an", "ek"} and _contains_any(
                text, (
                    "following me", "being followed", "sexual assault",
                    "sexually assaulted", "being assaulted", "balatkar", "rape",
                    "peecha kar raha", "peecha kar rahi",
                    "a family", "family inside", "child is being beaten",
                )
            )
            if not is_crime_actor and person_after_count.match(suffix):
                matches.append((match.start(), match.group(), numeric_value, False))
    for match in family_pattern.finditer(text):
        token = match.group("count").casefold()
        matches.append((match.start(), match.group("count"), count_words.get(token, -1), True))
    if matches:
        match_start, token, numeric_value, _ = max(
            matches, key=lambda item: (item[0], item[3])
        )
        token = token.casefold()
        if numeric_value >= 0:
            value = numeric_value
        elif token.isdecimal():
            digits = "".join(str(unicodedata.digit(char)) for char in token)
            value = int(digits)
        else:
            value = 2
        prefix = text[max(0, match_start - 24):match_start].casefold()
        approximate = _contains_any(prefix, (
            "around", "about", "approximately", "roughly", "सुमारे", "लगभग",
            "करीब", "આશરે", "લગભગ", "जवळपास", "lagbhag", "karib",
        ))
        return value, approximate, "explicit"

    if _contains_any(text, ("dozens", "दर्जनों", "darjano")):
        return RESEARCH_ASSUMPTION_VICTIM_COUNTS["dozens"], True, "plural_estimate"
    if _contains_any(text, (
        "many", "crowd", "mob", "भीड़", "कई", "घने", "ઘણા", "अनेक", "गर्दी",
        "bahut log", "kai log", "ghana loko", "anek lok", "bheed", "bheed mein",
    )):
        return RESEARCH_ASSUMPTION_VICTIM_COUNTS["many"], True, "plural_estimate"
    if _contains_any(text, (
        "people", "persons", "men", "women", "children", "kids", "babies",
        "family", "parivar", "workers", "passengers", "students", "members",
        "victims", "farmers", "girls", "old people", "elderly people",
        "bujurg", "buzurg", "kisaan", "kisan", "किसान", "किसानों", "लड़कियां",
        "ladkiyan", "ladkiyon", "mazdoor", "श्रमिक",         "परिवार", "કુટુંબ",
        "પરિવાર", "कुटुंब", "भीड़", "bheed",
        "बुजुर्ग", "वृद्ध", "लोक", "लोग", "log", "બાળકો", "લોકો",
        "માણસો", "શ્રમિકો", "शेतकरी", "माणसं", "मुले", "मुली",
    )):
        return RESEARCH_ASSUMPTION_VICTIM_COUNTS["plural"], True, "plural_estimate"

    if _contains_any(text, (
        "someone", "somebody", "a person", "my father", "my mother",
        "my husband", "my wife", "my son", "my daughter", "my friend",
        "he", "she", "ek aadmi",
    )) or _contains_any(text, _PERSON_NOUNS):
        return 1, False, "default"
    return None, False, "none"


def _extract_caller_request(text: str) -> str | None:
    for phrase in (
        "मदद चाहिए", "मुझे मदद चाहिए", "मदद भेजे", "मदद भेजो", "मदद भेजें",
        "कोई बचाओ", "मुझे बचाओ", "help करो", "please help", "send help", "please send help", "help me", "i need help",
        "भाई मदद करो", "मने मदद करो", "मदद भेजो", "मने मदद करो",
        "मला मदत हवी आहे", "मदत हवी आहे", "मदत पाठवा", "मला मदत करा",
        "मदत करा", "मदत कर", "मदत हवी आहे",
        "mujhe madad chahiye", "madad bhejo", "ambulance bhejo",
        "mane madad joie chhe", "madad moklo", "mala madat havi aahe", "madat pathva",
        "મારે મદદ જોઈએ છે", "મદદ મોકલો", "મને મદદ કરો",
        "ભાઈ મદદ કરો", "મને મદદ જોઈએ છે", "મદદ જોઈએ", "મદદ જોઇએ",
    ):
        if phrase in text:
            return phrase
    if "police" in text or "पुलिस" in text or "પોલીસ" in text:
        return "police"
    if "ambulance" in text or "एम्बुलेंस" in text:
        return "ambulance"
    if "help" in text:
        return "help"
    return None


_NON_GEOGRAPHIC_LOCATION_WORDS = {
    "arm", "back", "blood", "chest", "face", "foot", "hand", "head", "heart",
    "leg", "lung", "lungs", "neck", "pain", "shoulder", "stomach", "throat",
    "पेट", "हाथ", "पैर", "सिर", "छाती", "सीना", "चेस्ट", "दिल", "गला", "कमर", "खून",
    "दर्द", "इजा", "લોહી", "છાતી", "હાથ", "પગ", "માથું", "હૃદય", "પેટ",
    "દુખાવો", "ઇજા", "रक्त", "छाती", "हात", "पाय", "डोके", "हृदय", "पोट",
    "दुखणे", "दुखापत",
}


def _location_words(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(
        character
        for character in normalized
        if not unicodedata.category(character).startswith("M")
    )
    return set(re.findall(r"\w+", without_marks))


_NORMALIZED_NON_GEOGRAPHIC_LOCATION_WORDS = set().union(
    *(_location_words(word) for word in _NON_GEOGRAPHIC_LOCATION_WORDS)
)


def _is_non_geographic_location(candidate: str) -> bool:
    return bool(_location_words(candidate) & _NORMALIZED_NON_GEOGRAPHIC_LOCATION_WORDS)


def _extract_location(text: str, railway: bool) -> str | None:
    lowered = text.casefold()
    if ("विद्यानगर" in text or "विद्यानगरच्या" in text) and ("कॅन्टीन" in text or "कॅन्टीनमध्ये" in text) and "कॉलेज" in text:
        return "विद्यानगर, college canteen"
    gujarati_area_match = re.search(r"([\wÀ-࿔]+)\s+એરિયામાં", text, re.IGNORECASE)
    if gujarati_area_match and not _is_non_geographic_location(gujarati_area_match.group(1)):
        return f"{gujarati_area_match.group(1).strip()} વિસ્તાર"
    attached_place_match = re.search(r"([\wÀ-࿔]+)(?:માં|मध्ये|मध्ये)", text, re.IGNORECASE)
    attached_place = attached_place_match.group(1).strip() if attached_place_match else None
    place_match = re.search(
        r"([\wÀ-࿔]+)\s+(?:में|માં|માંના|मध्ये|एरियामध्ये|વિસ્તારમાં|एरियात)",
        text,
        re.IGNORECASE,
    )
    place = place_match.group(1).strip() if place_match else None
    if place and not _is_non_geographic_location(place) and "area" in lowered:
        return f"{place} area"
    if place and not _is_non_geographic_location(place) and ("એરિયા" in text or "વિસ્તાર" in text):
        return f"{place} વિસ્તાર"
    if place and not _is_non_geographic_location(place) and "college" in lowered and "canteen" in lowered:
        return f"{place}, college canteen"
    if place and not _is_non_geographic_location(place) and ("कॉलेज" in text or "કોલેજ" in text) and ("कैंटीन" in text or "કેન્ટીન" in text or "canteen" in lowered):
        return f"{place}, कॉलेज कैंटीन" if "कॉलेज" in text or "कैंटीन" in text else f"{place}, કોલેજ કેન્ટીન"
    if attached_place and not _is_non_geographic_location(attached_place):
        return attached_place
    if "college" in lowered and "canteen" in lowered:
        return "college canteen"
    if "college" in lowered:
        return "college"
    if "canteen" in lowered:
        return "canteen"
    if "કેન્ટીન" in text or "કેન્ટીન" in text:
        return "કેન્ટીન"
    if "कॅन्टीन" in text:
        return "कैंटीन"
    if "कॉलेज" in text or "कालेज" in text:
        return "कैंटीन" if "कैंटीन" in text else "कॉलेज"
    if "કોલેજ" in text or "કૉલેજ" in text:
        return "કેન્ટીન" if "કેન્ટીન" in text else "કોલેજ"
    if "कैंटीन" in text or "केंटीन" in text:
        return "कैंटीन"
    if not railway:
        match = re.search(r"([\wÀ-࿔]+(?:\s+[\wÀ-࿔]+){0,3})\s+(?:में|near|at|ke paas|ke samne|के पास|के सामने|ની પાસે|जवळ|जवळपास)", text, re.IGNORECASE)
        if match and not _is_non_geographic_location(match.group(1)):
            return match.group(1).strip()
    match = re.search(r"([\wÀ-࿔]+\s+(?:railway\s+station|रेलवे\s+स्टेशन))", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if "रेलवे स्टेशन" in text:
        return "रेलवे स्टेशन"
    if "railway station" in text:
        return "railway station"
    if "રેલવે સ્ટેશન" in text or "રેલવે સ્ટેશન" in text:
        return "રેલવે સ્ટેશન"
    if "સ્ટેશન" in text:
        return "रेलवे स्टेशन"
    if "स्थानक" in text:
        return "रेल्वे स्थानक"
    match = re.search(r"([\wÀ-࿔]+)\s+में", text)
    if match and not _is_non_geographic_location(match.group(1)):
        return match.group(1).strip()
    return None
