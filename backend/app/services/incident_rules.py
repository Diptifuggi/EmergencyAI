"""Deterministic incident fact extraction and service policy inputs.

The LLM may provide extraction hints, but these rules are authoritative for
classification and dispatch recommendations. They are decision support only;
a human dispatcher confirms every operational action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .emergency_keywords import evidence
from ..schemas.emergency_analysis import HelpRequired

_NEGATION_MARKERS = ("not ", "no ", "never ", "didn't ", "did not ", "wasn't ", "was not ")
_NON_LIVE_CONTEXT = ("movie", "story", "example", "joke", "training example")
_COUNT_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
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
            context = text[max(0, start - 24):start]
            if not any(marker in context for marker in _NEGATION_MARKERS):
                return True
            start = text.find(phrase, start + len(phrase))
    return False


@dataclass(frozen=True)
class IncidentFacts:
    emergency_type: str
    sub_type: str | None
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
    emergency_keywords: list[str] = field(default_factory=list)


def services_for_facts(facts: IncidentFacts) -> list[HelpRequired]:
    """Derive services only from explicit incident evidence."""
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
    contextual = any(marker in normalized for marker in _NON_LIVE_CONTEXT)
    flags = evidence(text, language)
    hit = {name: _contains(normalized, phrases) for name, phrases in _PHRASES.items()}
    if contextual:
        hit = {name: False for name in hit}

    medical = bool(flags.get("medical"))
    injury = bool(flags.get("injury") or flags.get("bleeding") or flags.get("unconscious"))
    fire = bool(flags.get("fire") or flags.get("explosion"))
    trapped = bool(flags.get("trapped") or flags.get("rescue"))
    railway = bool(flags.get("railway"))
    road = bool(flags.get("road") or flags.get("accident"))
    highway = bool(flags.get("highway"))
    cyber = bool(flags.get("cybercrime"))
    lpg = bool(flags.get("lpg"))
    active_crime = bool(hit["active"] and (hit["crime"] or hit["burglary"] or hit["robbery"] or hit["violence"] or hit["home_intrusion"]))
    home = hit["home_intrusion"] or (hit["burglary"] and ("house" in normalized or "home" in normalized))
    burglary = bool(home and (hit["burglary"] or hit["home_intrusion"]))
    robbery = bool(hit["robbery"] and (active_crime or hit["active"]))
    assault = bool(hit["violence"] and (active_crime or hit["active"]))
    weapon = bool(hit["weapon"] or flags.get("weapon"))
    police = bool(
        hit["police_request"] or hit["crime"] or hit["burglary"] or hit["robbery"]
        or hit["violence"] or flags.get("police") or hit["domestic"]
        or hit["missing"] or weapon or (road and flags.get("major"))
    )
    immediate = bool(active_crime or weapon or hit["domestic"] or hit["missing"] or (flags.get("immediate") and (police or medical or fire)))

    if cyber:
        kind, subtype = "cybercrime", "online_fraud"
    elif lpg:
        kind, subtype = "lpg", "gas_leak"
    elif fire:
        kind, subtype = "fire", "fire_or_explosion"
    elif medical and not (road or railway):
        kind, subtype = "medical", "medical_emergency"
    elif road or railway:
        kind, subtype = "accident", "railway_accident" if railway else "road_accident"
    elif hit["missing"]:
        kind, subtype = "child_safety", "missing_child"
    elif police and ("following me" in normalized or "being followed" in normalized):
        kind, subtype = "women_safety", "threat_or_stalking"
    elif police and (active_crime or weapon or hit["domestic"]):
        kind, subtype = "crime_police", "burglary_home_intrusion" if burglary else "active_crime"
    elif police:
        kind, subtype = "police", "police_assistance"
    elif hit["missing"]:
        kind, subtype = "child_safety", "missing_child"
    else:
        kind, subtype = "unknown", None

    keyword_candidates = [phrase for name, phrases in _PHRASES.items() if hit.get(name) for phrase in phrases if phrase in normalized]
    if flags.get("medical"):
        keyword_candidates.extend(phrase for phrase in ("chest pain", "difficulty breathing", "ambulance") if phrase in normalized)
    keywords = list(dict.fromkeys(keyword_candidates))[:20]
    victim_count = _extract_victim_count(normalized)
    return IncidentFacts(
        emergency_type=kind,
        sub_type=subtype,
        immediate_danger=immediate,
        crime_in_progress=active_crime,
        police_required=police,
        medical_emergency=medical,
        injuries_present=injury,
        severe_bleeding=bool(flags.get("bleeding")),
        unconscious_person=bool(flags.get("unconscious")),
        fire_present=fire,
        smoke_present=bool(hit["smoke"]),
        explosion_present=bool(flags.get("explosion")),
        rescue_required=trapped,
        trapped_persons=trapped,
        weapon_present=weapon,
        weapon_type="gun" if hit["gun"] else ("knife" if "knife" in normalized else None),
        victim_count=victim_count,
        children_involved=bool(hit["child"] or flags.get("child_missing")),
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
        caller_request="police" if hit["police_request"] else ("ambulance" if "ambulance" in normalized else None),
        emergency_keywords=keywords,
    )


def _extract_victim_count(text: str) -> int | None:
    """Extract only directly stated people counts; never infer a count."""
    numeric = re.search(r"\b(\d{1,3})\s+(?:people|persons|victims|casualties|patients)\b", text)
    if numeric:
        return int(numeric.group(1))
    for word, count in _COUNT_WORDS.items():
        if re.search(rf"\b{word}\s+(?:people|persons|victims|casualties|patients)\b", text):
            return count
    return None
