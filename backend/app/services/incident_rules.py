"""Deterministic incident fact extraction and service policy inputs.

The LLM may provide extraction hints, but these rules are authoritative for
classification and dispatch recommendations. They are decision support only;
a human dispatcher confirms every operational action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .emergency_keywords import KEYWORDS, evidence
from .emergency_lexicon import lexicon_matches
from ..schemas.emergency_analysis import HelpRequired

_NEGATION_MARKERS = ("not ", "no ", "never ", "didn't ", "did not ", "wasn't ", "was not ")
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
)
_NEGATED_INCIDENT_MARKERS = (
    "no accident", "no fire", "no explosion", "nothing happened", "accident नहीं", "accident नहीं हुआ", "no fire", "fire नहीं", "आग नहीं", "आग नहीं लगी", "धमाका नहीं हुआ", "गैस लीक नहीं है", "कोई खतरा नहीं",
    "कोई accident नहीं", "હાદસો નથી", "થયો નથી", "થયું નથી", "આગ લાગી નથી", "ગેસ લીક નથી", "કોઈ ખતરો નથી", "अपघात नाही", "नाही झाले", "झाले नाही", "आग लागली नाही", "गॅस गळती नाही", "धोका नाही",
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
_COUNT_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_DEVANAGARI_COUNT_WORDS = {
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5,
    "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14, "पंद्रह": 15,
    "पन्द्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18, "उन्नीस": 19,
    "बीस": 20, "इक्कीस": 21, "बाईस": 22, "तेईस": 23, "चौबीस": 24,
    "पच्चीस": 25, "छब्बीस": 26, "सत्ताईस": 27, "अट्ठाईस": 28,
    "उनतीस": 29, "तीस": 30, "चालीस": 40, "पचास": 50, "सौ": 100,
}

_PHRASES: dict[str, tuple[str, ...]] = {
    "home_intrusion": (
        "breaking into my house", "breaking into my home", "broke into my house",
        "broke into my home", "home intrusion", "house break-in", "home break-in",
        "intruder in my house", "intruder in my home", "someone is inside my house",
        "someone is inside my home", "someone entered my house", "someone entered my home",
        "stranger inside my house", "stranger inside my home",
    ),
    "burglary": ("burglary", "burglar", "burglars", "breaking in", "break-in"),
    "robbery": ("robbery", "robber", "robbers", "someone is robbing me", "stealing right now", "someone is stealing"),
    "crime": ("crime happening", "crime in progress", "criminal", "thief", "thieves", "theft happening"),
    "police_request": ("police help", "need police", "send police", "police immediately", "police assistance", "police assistant"),
    "active": ("right now", "currently", "happening now", "at this moment", "breaking in", "attacking me", "chasing me", "stealing right now", "following me", "being followed"),
    "violence": ("attack", "attacking me", "assault", "being assaulted", "fight", "violent person", "threatening me"),
    "weapon": ("gun", "pistol", "rifle", "knife", "weapon", "armed", "firearm", "holding a gun", "threatening me with a knife"),
    "gun": ("gun", "pistol", "rifle", "firearm"),
    "domestic": ("domestic violence", "my husband is beating me", "my wife is attacking me", "partner is hitting me", "family member is threatening me", "my husband is threatening me"),
    "sexual": ("sexual assault", "sexually assaulted", "rape", "molestation"),
    "child": ("my child", "my son", "my daughter", "child is missing", "child is trapped", "kidnapped my child", "child is injured", "child is in danger"),
    "elderly": ("elderly", "senior citizen", "old person", "grandfather", "grandmother"),
    "missing": ("child is missing", "my child is missing", "missing person", "cannot find my child"),
    "smoke": ("smoke everywhere", "smoke in", "heavy smoke"),
    "distress": ("scared", "afraid", "frightened", "save me"),
}


def _contains(text: str, phrases: tuple[str, ...]) -> bool:
    for phrase in phrases:
        start = text.find(phrase)
        while start >= 0:
            context = text[max(0, start - 36):start]
            following = text[start + len(phrase):start + len(phrase) + 30]
            markers = _NEGATION_MARKERS + ("नहीं ", "कोई नहीं", "नहीं", "નથી", "નહીં", "નાહી", "nahi ", "nahin ")
            following_negated = (
                any(marker in following for marker in ("नहीं", "નથી", "नाही"))
                or following.startswith("not ")
                or " not " in following
            )
            if not any(marker in context for marker in markers) and not following_negated:
                return True
            start = text.find(phrase, start + len(phrase))
    return False


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
    caller_request: str | None
    location_description: str | None
    emergency_keywords: list[str] = field(default_factory=list)


def services_for_facts(facts: IncidentFacts) -> list[HelpRequired]:
    """Derive services only from explicit incident evidence."""
    if not facts.current_emergency:
        return []
    services: list[HelpRequired] = []
    if facts.police_required:
        services.append(HelpRequired.POLICE)
    if facts.medical_emergency or facts.injuries_present or facts.severe_bleeding or facts.unconscious_person:
        services.extend([HelpRequired.AMBULANCE, HelpRequired.MEDICAL_ASSISTANCE])
    if facts.fire_present or facts.explosion_present:
        services.append(HelpRequired.FIRE_SERVICE)
    if facts.rescue_required or facts.trapped_persons:
        services.append(HelpRequired.RESCUE)
        if facts.fire_present and HelpRequired.AMBULANCE not in services:
            services.insert(0, HelpRequired.AMBULANCE)
    if facts.domestic_violence:
        services.append(HelpRequired.WOMEN_SAFETY_SUPPORT)
    if facts.emergency_type == "women_safety":
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
    drill = any(marker in normalized for marker in ("fire drill", "emergency drill", "practice drill"))
    hypothetical = any(marker in normalized for marker in (
        "what should i do if", "if an accident happens", "if there is an accident",
        "what if", "suppose", "supposing", "in case", "if this happens",
        "જો અકસ્માત થાય તો", "જો આગ લાગે", "જો ગેસ લીક થાય", "જો સિલિન્ડર ફાટે", "જો આવું થાય",
        "जर असे झाले", "जर आग लागली", "जर गॅस गळला", "जर अपघात झाला",
        "अगर ट्रेन हादसा हो जाए", "अगर हादसा हो", "अगर accident हो जाए", "अगर आग लग जाए", "अगर गैस लीक हो जाए", "अगर गैस सिलेंडर फट जाए",
        "अगर किसी को", "अगर कोई", "if there is a fire",
    )) or drill
    historical = any(marker in normalized for marker in (
        "yesterday", "last night", "last week", "last month", "earlier", "previously", "historically", "कल", "कल रात", "पिछले हफ्ते", "पिछले महीने", "कुछ दिन पहले", "हुआ था", "गई थी", "गया था", "ગઈકાલે", "ગઈ રાતે", "ગયા અઠવાડિયે", "થયું હતું", "झाले होते", "काल", "काल रात्री", "गेल्या आठवड्यात",
    ))
    resolved = any(marker in normalized for marker in (
        "now everything is fine", "now all is well", "now it is controlled", "ambulance has arrived", "police already reached", "everything is fine now", "situation is under control", "fire is out", "person is safe", "no longer dangerous", "problem resolved", "emergency is over", "everyone is safe",
        "अब सब ठीक", "अब सब सुरक्षित", "स्थिति नियंत्रण में", "आग बुझ गई", "आग पर काबू पा लिया", "अब जरूरत नहीं", "अब खतरा नहीं", "समस्या हल हो गई", "इमरजेंसी खत्म हो गई", "सब सुरक्षित", "पुलिस पहुंच गई",
        "હવે બધું ઠીક", "હવે બધા સુરક્ષિત", "પરિસ્થિતિ કાબૂમાં", "આગ બુઝાઈ ગઈ", "હવે ખતરો નથી", "સમસ્યા ઉકેલાઈ ગઈ", "ઇમરજન્સી પૂરી થઈ",
        "आता सर्व ठीक", "आता सगळे सुरक्षित", "परिस्थिती नियंत्रणात", "आग विझली", "आग आटोक्यात", "आता धोका नाही", "समस्या सुटली", "आणीबाणी संपली",
    ))
    uncertain = any(marker in normalized for marker in _UNCERTAINTY_MARKERS)
    negated = any(marker in normalized for marker in _NEGATED_INCIDENT_MARKERS)
    contextual = hypothetical or historical or resolved or uncertain or negated or any(marker in normalized for marker in _NON_LIVE_CONTEXT)
    flags = evidence(text, language)
    hit = {name: _contains(normalized, phrases) for name, phrases in _PHRASES.items()}
    if contextual:
        hit = {name: False for name in hit}
    if hypothetical or uncertain or negated:
        flags = {name: False for name in flags}

    domains = lexicon_matches(text, language)
    if hypothetical or uncertain or negated:
        domains = {}

    medical = bool(flags.get("medical"))
    injury = bool(flags.get("injury") or flags.get("bleeding") or flags.get("unconscious"))
    lpg = bool(flags.get("lpg") or any(marker in normalized for marker in _LPG_HINTS))
    explosion = bool(flags.get("explosion") or any(marker in normalized for marker in _EXPLOSION_HINTS))
    fire = bool(flags.get("fire") or explosion)
    trapped = bool(flags.get("trapped") or flags.get("rescue"))
    railway = bool(flags.get("railway"))
    accident_evidence = bool(flags.get("accident"))
    road = bool(flags.get("road") or (flags.get("highway") and accident_evidence))
    highway = bool(flags.get("highway"))
    cyber = bool(flags.get("cybercrime"))
    drowning = "drowning" in domains
    structural_collapse = "structural_collapse" in domains
    natural_disaster = "natural_disaster" in domains
    electrical_incident = "electrical" in domains
    hazmat_incident = "chemical_hazmat" in domains
    animal_attack = "animal_attack" in domains
    crowd_emergency = "crowd_emergency" in domains
    self_harm_crisis = "self_harm_crisis" in domains
    medical = medical or drowning or animal_attack or self_harm_crisis
    injury = injury or animal_attack or crowd_emergency
    trapped = trapped or drowning or structural_collapse or natural_disaster or crowd_emergency
    active_crime = bool(hit["active"] and (hit["crime"] or hit["burglary"] or hit["robbery"] or hit["violence"] or hit["home_intrusion"]))
    home = hit["home_intrusion"] or (hit["burglary"] and ("house" in normalized or "home" in normalized))
    burglary = bool(home and (hit["burglary"] or hit["home_intrusion"]))
    robbery = bool(hit["robbery"] and (active_crime or hit["active"]))
    assault = bool(hit["violence"] and (active_crime or hit["active"]))
    weapon = bool(hit["weapon"] or flags.get("weapon"))
    children_involved = bool(
        hit["child"] or flags.get("child") or flags.get("child_missing")
    )
    police = bool(
        hit["police_request"] or hit["crime"] or hit["burglary"] or hit["robbery"]
        or hit["violence"] or flags.get("police") or hit["domestic"]
        or hit["missing"] or weapon or crowd_emergency
    )
    immediate = bool(active_crime or weapon or hit["domestic"] or hit["missing"] or drowning or structural_collapse or crowd_emergency or self_harm_crisis or (flags.get("immediate") and (police or medical or fire)))
    fire = bool(flags.get("fire") or explosion or hazmat_incident or (electrical_incident and "fire" in normalized))
    rescue_required = trapped or bool(lpg and explosion)
    location_description = _extract_location(text, railway)

    if hypothetical:
        kind, subtype = "unknown", None
    elif cyber:
        kind, subtype = "cybercrime", "online_fraud"
    elif lpg and (explosion or "gas leak" in normalized or "gas leakage" in normalized):
        kind, subtype = "lpg", "lpg_gas_explosion" if explosion else "gas_leak"
    elif lpg:
        kind, subtype = "lpg", "gas_leak"
    elif structural_collapse:
        kind, subtype = "disaster", "structural_collapse"
    elif natural_disaster:
        kind, subtype = "disaster", "natural_disaster"
    elif drowning:
        kind, subtype = "medical", "drowning"
    elif hazmat_incident:
        kind, subtype = "disaster", "chemical_hazmat"
    elif electrical_incident:
        kind, subtype = "medical", "electrical_emergency"
    elif animal_attack:
        kind, subtype = "medical", "animal_attack"
    elif crowd_emergency:
        kind, subtype = "disaster", "crowd_emergency"
    elif self_harm_crisis:
        kind, subtype = "medical", "self_harm_crisis"
    elif fire:
        kind, subtype = "fire", "fire_or_explosion"
    elif children_involved and injury:
        kind, subtype = "child_safety", "injured_child"
    elif medical and not (road or railway):
        kind, subtype = "medical", "medical_emergency"
    elif road or railway or accident_evidence:
        kind, subtype = (
            "accident",
            "railway_accident" if railway else "road_accident" if road else "unknown_accident",
        )
    elif hit["missing"]:
        kind, subtype = "child_safety", "missing_child"
    elif police and ("following me" in normalized or "being followed" in normalized):
        kind, subtype = "women_safety", "threat_or_stalking"
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
    if flags.get("medical"):
        keyword_candidates.extend(phrase for phrase in ("chest pain", "difficulty breathing", "ambulance") if phrase in normalized)
    keywords = list(dict.fromkeys(keyword_candidates))[:20]
    victim_count, victim_count_approximate = _extract_victim_count(normalized)
    if uncertain:
        victim_count, victim_count_approximate = None, False
    caller_request = _extract_caller_request(normalized)
    if not caller_request and "help" in normalized:
        caller_request = "help"

    return IncidentFacts(
        emergency_type=kind,
        sub_type=subtype,
        non_live_context=contextual,
        context_state=("hypothetical" if hypothetical else "resolved" if resolved else "historical" if historical else "uncertain" if uncertain else "current"),
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
        children_involved=children_involved,
        elderly_involved=bool(hit["elderly"] or flags.get("elderly")),
        domestic_violence=hit["domestic"],
        sexual_violence=hit["sexual"],
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
        caller_request=caller_request,
        location_description=location_description,
        emergency_keywords=keywords,
    )


def _extract_victim_count(text: str) -> tuple[int | None, bool]:
    """Return the latest explicit count and whether it is approximate."""
    count_tokens = "|".join(
        sorted((re.escape(word) for word in (*_COUNT_WORDS, *_DEVANAGARI_COUNT_WORDS)), key=len, reverse=True)
    )
    pattern = re.compile(
        rf"(?P<approx>around|about|approximately|roughly|सुमारे|लगभग|करीब|આશરે|जवळपास)?\s*"
        rf"(?P<count>\d{{1,3}}|{count_tokens})\s+"
        r"(?:people|persons|victims|casualties|patients|लोग|व्यक्ति|घायल|घायल हैं|बच्चा|बच्चे|लोक|जखमी)",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return None, False
    match = matches[-1]
    token = match.group("count")
    if token.isdigit():
        value = int(token)
    else:
        value = _COUNT_WORDS.get(token.lower()) or _DEVANAGARI_COUNT_WORDS.get(token)
    return value, bool(match.group("approx"))


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


def _extract_location(text: str, railway: bool) -> str | None:
    lowered = text.casefold()
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
        if match:
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
    if match:
        return match.group(1).strip()
    return None
