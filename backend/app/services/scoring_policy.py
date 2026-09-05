"""Central deterministic scoring policy for EmergencyIQ analysis.

LLM output is probabilistic extraction, not a dispatch decision. Scores are
normalized to 0--100 and categories are derived using fixed, project-defined
research thresholds. These thresholds are not an official 112 standard.
"""
from __future__ import annotations

from ..schemas.emergency_analysis import AnalysisLevel
from ..schemas.emergency_analysis import EmergencyType, HelpRequired
from .emergency_keywords import evidence
from .emergency_service_directory import numbers_for_services


def clamp_score(value: int | float) -> int:
    """Safely normalize a model-provided numeric indicator to the 0--100 range."""
    return max(0, min(100, int(value)))


def level_for_score(score: int | float) -> AnalysisLevel:
    """The sole categorical mapping used for priority, stress and panic."""
    normalized = clamp_score(score)
    if normalized <= 25:
        return AnalysisLevel.LOW
    if normalized <= 50:
        return AnalysisLevel.MEDIUM
    if normalized <= 75:
        return AnalysisLevel.HIGH
    return AnalysisLevel.CRITICAL


_TYPE_BASE = {
    EmergencyType.OTHER: 10, EmergencyType.UNKNOWN: 10, EmergencyType.CRIME_POLICE: 45,
    EmergencyType.ACCIDENT: 20, EmergencyType.POLICE: 30,
    EmergencyType.WOMEN_SAFETY: 30, EmergencyType.DOMESTIC_VIOLENCE: 35,
    EmergencyType.CHILD_SAFETY: 35, EmergencyType.ROBBERY: 35,
    EmergencyType.HARASSMENT: 30, EmergencyType.ASSAULT: 40,
    EmergencyType.MEDICAL: 40, EmergencyType.FIRE: 50, EmergencyType.DISASTER: 55,
    EmergencyType.CYBERCRIME: 35, EmergencyType.LPG: 45,
}


def calculate_severity_score(*, emergency_type: EmergencyType, transcript: str, language: str = "en") -> int:
    """Calculate severity only from type and transcript evidence, never an LLM label."""
    score = _TYPE_BASE[emergency_type]
    flags = evidence(transcript, language)
    if flags.get("major"):
        score += 30 if emergency_type == EmergencyType.ACCIDENT else 20
        if emergency_type == EmergencyType.ACCIDENT and flags.get("injury"):
            score += 20
    elif flags.get("injury") or flags.get("medical"):
        score += 30 if emergency_type == EmergencyType.ACCIDENT and flags.get("injury") else 20
    if flags.get("trapped") or flags.get("rescue"):
        score += 25
    # Fire is an additional escalation for an accident; it is already inherent
    # in a fire classification's base score.
    if emergency_type != EmergencyType.FIRE and (flags.get("fire") or flags.get("explosion")):
        score += 25
    if flags.get("police") or flags.get("weapon"):
        score += 15
    if emergency_type == EmergencyType.ACCIDENT and flags.get("no_injury"):
        score -= 10
    return clamp_score(score)


def calculate_priority_score(*, emergency_type: EmergencyType, immediate_threat: bool,
                             people_at_risk: int, transcript: str, language: str = "en") -> int:
    """Calculate normalized decision-support priority from explicit evidence.

    Priority starts with deterministic severity. Active threat/urgent request and
    directly stated people at risk add urgency. LLM scores, labels, panic, and
    stress are deliberately not hidden multipliers in this policy.
    """
    score = calculate_severity_score(emergency_type=emergency_type, transcript=transcript, language=language)
    flags = evidence(transcript, language)
    if immediate_threat or flags.get("immediate"):
        # Urgency raises an accident to HIGH; fire, entrapment, unconsciousness,
        # or weapons provide the stronger evidence for CRITICAL.
        score += 5 if emergency_type == EmergencyType.ACCIDENT else 15
    if emergency_type == EmergencyType.CHILD_SAFETY and flags.get("child_missing"):
        score += 15
    score += min(max(0, people_at_risk), 4) * 5
    return clamp_score(score)


def calculate_help_required(*, emergency_type: EmergencyType, transcript: str, language: str = "en",
                            victim_count: int | None = None, injuries_present: bool = False,
                            medical_emergency: bool = False, fire_present: bool = False,
                            explosion_present: bool = False, trapped_persons: bool = False,
                            rescue_required: bool = False) -> list[HelpRequired]:
    """Select services from type plus explicit transcript evidence only.

    This is decision support, not an autonomous dispatch instruction.  In
    particular, an accident does not imply an ambulance or fire service without
    injury, entrapment, or fire evidence.
    """
    flags = evidence(transcript, language)
    # LLM booleans are extraction hints only; explicit transcript evidence is
    # authoritative for dispatch-related decisions.
    injured = (flags.get("injury", False) or flags.get("bleeding", False) or
               flags.get("unconscious", False)) and not flags.get("no_injury", False)
    trapped = flags.get("trapped", False) or flags.get("rescue", False)
    fire = flags.get("fire", False) or flags.get("explosion", False)
    medical = medical_emergency or flags.get("medical", False)
    major_accident = emergency_type == EmergencyType.ACCIDENT and flags.get("major", False)
    help_required: list[HelpRequired] = []
    if emergency_type in {EmergencyType.POLICE, EmergencyType.WOMEN_SAFETY,
                          EmergencyType.DOMESTIC_VIOLENCE, EmergencyType.CHILD_SAFETY,
                          EmergencyType.ROBBERY, EmergencyType.ASSAULT, EmergencyType.HARASSMENT}:
        help_required.append(HelpRequired.POLICE)
    if emergency_type == EmergencyType.ACCIDENT:
        help_required.append(HelpRequired.POLICE)
    if emergency_type == EmergencyType.CYBERCRIME:
        help_required.extend([HelpRequired.POLICE, HelpRequired.CYBERCRIME])
    if emergency_type == EmergencyType.LPG:
        help_required.append(HelpRequired.LPG)
    if emergency_type == EmergencyType.FIRE or fire:
        help_required.append(HelpRequired.FIRE_SERVICE)
    if emergency_type == EmergencyType.MEDICAL or medical or injured or major_accident:
        help_required.append(HelpRequired.AMBULANCE)
    if trapped:
        help_required.extend([HelpRequired.FIRE_SERVICE, HelpRequired.RESCUE])
        if HelpRequired.AMBULANCE not in help_required:
            help_required.append(HelpRequired.AMBULANCE)
    if emergency_type == EmergencyType.DISASTER and not trapped:
        help_required.append(HelpRequired.MULTIPLE_SERVICES)
    if not help_required:
        return [HelpRequired.UNKNOWN]
    ordered = list(dict.fromkeys(help_required))
    if HelpRequired.AMBULANCE in ordered:
        ordered.remove(HelpRequired.AMBULANCE)
        ordered.insert(0, HelpRequired.AMBULANCE)
    return ordered


def recommended_units_for_help(help_required: list[HelpRequired]) -> list[str]:
    """Derive visible unit recommendations from validated required services."""
    return [item.value for item in help_required if item not in {HelpRequired.UNKNOWN, HelpRequired.MULTIPLE_SERVICES}]


def emergency_numbers_for_help(help_required: list[HelpRequired]) -> dict[str, list[str]]:
    return numbers_for_services(recommended_units_for_help(help_required))
