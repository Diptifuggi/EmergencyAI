from __future__ import annotations

from ..schemas.emergency_analysis import AnalysisLevel, EmergencyType, HelpRequired

_VALID_EMERGENCY_TYPES = {item.value for item in EmergencyType}
_VALID_HELP_REQUIRED = {item.value for item in HelpRequired}
_VALID_LEVELS = {item.value for item in AnalysisLevel}

_EMERGENCY_TYPE_ALIASES: dict[str, str] = {
    "woman_safety": "women_safety",
    "women_safety": "women_safety",
    "domestic_violence": "domestic_violence",
    "domesticviolence": "domestic_violence",
    "child_safety": "child_safety",
    "childsafety": "child_safety",
    "road_accident": "accident",
    "car_accident": "accident",
    "medical_emergency": "medical",
    "theft": "robbery",
    "general": "other",
    "none": "unknown",
}

_HELP_REQUIRED_ALIASES: dict[str, str] = {
    "medical": "medical_assistance",
    "medical_help": "medical_assistance",
    "medical_assist": "medical_assistance",
    "doctor": "medical_assistance",
    "ems": "ambulance",
    "paramedic": "ambulance",
    "hospital": "ambulance",
    "fire": "fire_service",
    "fire_department": "fire_service",
    "fire_brigade": "fire_service",
    "firefighters": "fire_service",
    "firefighter": "fire_service",
    "women_safety": "women_safety_support",
    "women_safety_help": "women_safety_support",
    "child_safety": "child_protection",
    "child_welfare": "child_protection",
    "multiple": "multiple_services",
    "multiple_service": "multiple_services",
    "all": "multiple_services",
    "none": "unknown",
}

_DISPATCH_UNIT_ALIASES: dict[str, str] = {
    **_HELP_REQUIRED_ALIASES,
    "fire_service": "fire_service",
    "police": "police",
    "ambulance": "ambulance",
    "rescue": "rescue",
}


def _clean_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def normalize_emergency_type(value: str) -> EmergencyType:
    cleaned = _clean_token(value)
    mapped = _EMERGENCY_TYPE_ALIASES.get(cleaned, cleaned)
    if mapped in _VALID_EMERGENCY_TYPES:
        return EmergencyType(mapped)
    return EmergencyType.UNKNOWN


def normalize_help_required(value: str) -> HelpRequired | None:
    cleaned = _clean_token(value)
    mapped = _HELP_REQUIRED_ALIASES.get(cleaned, cleaned)
    if mapped in _VALID_HELP_REQUIRED:
        return HelpRequired(mapped)
    return None


def normalize_help_required_list(values: list[str]) -> list[HelpRequired]:
    normalized: list[HelpRequired] = []
    seen: set[HelpRequired] = set()
    for value in values:
        if not value or not value.strip():
            continue
        item = normalize_help_required(value)
        if item is not None and item not in seen:
            seen.add(item)
            normalized.append(item)
    return normalized


def normalize_analysis_level(value: str) -> AnalysisLevel:
    cleaned = value.strip().upper()
    aliases = {
        "MODERATE": AnalysisLevel.MEDIUM,
        "SEVERE": AnalysisLevel.HIGH,
        "URGENT": AnalysisLevel.HIGH,
        "EMERGENCY": AnalysisLevel.CRITICAL,
    }
    if cleaned in _VALID_LEVELS:
        return AnalysisLevel(cleaned)
    return aliases.get(cleaned, AnalysisLevel.MEDIUM)


def priority_level_to_db_value(level: AnalysisLevel) -> str:
    """Map analysis priority_level to emergency_calls.priority column."""
    return level.value.lower()


_EMERGENCY_TYPE_DEFAULT_HELP: dict[EmergencyType, list[HelpRequired]] = {
    EmergencyType.MEDICAL: [HelpRequired.MEDICAL_ASSISTANCE, HelpRequired.AMBULANCE],
    EmergencyType.POLICE: [HelpRequired.POLICE],
    EmergencyType.FIRE: [HelpRequired.FIRE_SERVICE],
    EmergencyType.ACCIDENT: [HelpRequired.POLICE, HelpRequired.AMBULANCE],
    EmergencyType.WOMEN_SAFETY: [HelpRequired.POLICE, HelpRequired.WOMEN_SAFETY_SUPPORT],
    EmergencyType.DOMESTIC_VIOLENCE: [HelpRequired.POLICE, HelpRequired.WOMEN_SAFETY_SUPPORT],
    EmergencyType.CHILD_SAFETY: [HelpRequired.POLICE, HelpRequired.CHILD_PROTECTION],
    EmergencyType.ROBBERY: [HelpRequired.POLICE],
    EmergencyType.ASSAULT: [HelpRequired.POLICE, HelpRequired.AMBULANCE],
    EmergencyType.HARASSMENT: [HelpRequired.POLICE],
    EmergencyType.DISASTER: [HelpRequired.RESCUE, HelpRequired.MULTIPLE_SERVICES],
}

_TRANSCRIPT_HELP_HINTS: tuple[tuple[tuple[str, ...], HelpRequired], ...] = (
    (("medical", "injured", "injury", "unconscious", "bleeding", "heart attack", "stroke"), HelpRequired.MEDICAL_ASSISTANCE),
    (("ambulance", "hospital", "ems", "paramedic"), HelpRequired.AMBULANCE),
    (("police", "thief", "robbery", "assault", "following", "weapon", "stolen"), HelpRequired.POLICE),
    (("fire", "smoke", "burning", "flames"), HelpRequired.FIRE_SERVICE),
    (("trapped", "collapsed", "flood", "earthquake"), HelpRequired.RESCUE),
    (("child", "minor"), HelpRequired.CHILD_PROTECTION),
    (("woman", "women", "harass", "stalk"), HelpRequired.WOMEN_SAFETY_SUPPORT),
)


def _dedupe_help(values: list[HelpRequired]) -> list[HelpRequired]:
    seen: set[HelpRequired] = set()
    deduped: list[HelpRequired] = []
    for item in values:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def enrich_help_required(
    *,
    help_required: list[HelpRequired],
    emergency_type: EmergencyType,
    transcript: str,
    dispatch_units: list[str],
) -> list[HelpRequired]:
    """
    Replace vague LLM output (e.g. only unknown) with transcript/type/dispatch hints.
    """
    inferred: list[HelpRequired] = list(help_required)

    for unit in dispatch_units:
        mapped = normalize_help_required(unit)
        if mapped is not None:
            inferred.append(mapped)

    inferred.extend(_EMERGENCY_TYPE_DEFAULT_HELP.get(emergency_type, []))

    lower = transcript.lower()
    for keywords, help_value in _TRANSCRIPT_HELP_HINTS:
        if any(keyword in lower for keyword in keywords):
            inferred.append(help_value)

    concrete = [item for item in _dedupe_help(inferred) if item != HelpRequired.UNKNOWN]
    if concrete:
        return concrete

    if help_required:
        return _dedupe_help(help_required)
    return [HelpRequired.UNKNOWN]


def normalize_dispatch_units(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or not value.strip():
            continue
        cleaned = _clean_token(value)
        mapped = _DISPATCH_UNIT_ALIASES.get(cleaned, cleaned)
        if mapped not in seen:
            seen.add(mapped)
            normalized.append(mapped)
    return normalized
