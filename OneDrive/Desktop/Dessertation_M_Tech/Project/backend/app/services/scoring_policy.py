"""Central deterministic scoring policy for EmergencyIQ analysis.

LLM output is probabilistic extraction, not a dispatch decision. Scores are
normalized to 0--100 and categories are derived using fixed, project-defined
research thresholds. These thresholds are not an official 112 standard.
"""
from __future__ import annotations

from ..schemas.emergency_analysis import AnalysisLevel
from ..schemas.emergency_analysis import EmergencyType, HelpRequired


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
    EmergencyType.OTHER: 10, EmergencyType.UNKNOWN: 10,
    EmergencyType.ACCIDENT: 20, EmergencyType.POLICE: 30,
    EmergencyType.WOMEN_SAFETY: 30, EmergencyType.DOMESTIC_VIOLENCE: 35,
    EmergencyType.CHILD_SAFETY: 35, EmergencyType.ROBBERY: 35,
    EmergencyType.HARASSMENT: 30, EmergencyType.ASSAULT: 40,
    EmergencyType.MEDICAL: 40, EmergencyType.FIRE: 50, EmergencyType.DISASTER: 55,
}
_MAJOR_CUES = ("major accident", "major crash", "severe", "badly injured", "unconscious", "bleeding", "chest pain", "heart attack")
_TRAPPED_CUES = ("trapped", "collapsed", "entrapment")
_FIRE_CUES = ("on fire", "vehicle fire", "fire", "flames", "smoke", "burning")
_SAFETY_THREAT_CUES = ("following me", "being followed", "weapon", "gun", "knife", "assault")
_IMMEDIATE_REQUEST_CUES = ("immediate", "urgent", "help now", "send police", "send ambulance", "please send", "need police help")
_INJURY_CUES = ("injured", "injury", "bleeding", "unconscious", "chest pain", "heart attack")
_NO_INJURY_CUES = ("nobody is injured", "no one is injured", "no injuries", "not injured")
_MEDICAL_CUES = ("medical help", "medical emergency", "need a doctor", "need doctor")


def calculate_severity_score(*, emergency_type: EmergencyType, transcript: str) -> int:
    """Calculate severity only from type and transcript evidence, never an LLM label."""
    score = _TYPE_BASE[emergency_type]
    text = transcript.lower()
    if any(cue in text for cue in _MAJOR_CUES):
        score += 20
    if any(cue in text for cue in _TRAPPED_CUES):
        score += 25
    # Fire is an additional escalation for an accident; it is already inherent
    # in a fire classification's base score.
    if emergency_type != EmergencyType.FIRE and any(cue in text for cue in _FIRE_CUES):
        score += 25
    if any(cue in text for cue in _SAFETY_THREAT_CUES):
        score += 15
    if emergency_type == EmergencyType.ACCIDENT and any(cue in text for cue in _NO_INJURY_CUES):
        score -= 10
    return clamp_score(score)


def calculate_priority_score(*, emergency_type: EmergencyType, immediate_threat: bool,
                             people_at_risk: int, transcript: str) -> int:
    """Calculate normalized decision-support priority from explicit evidence.

    Priority starts with deterministic severity. Active threat/urgent request and
    directly stated people at risk add urgency. LLM scores, labels, panic, and
    stress are deliberately not hidden multipliers in this policy.
    """
    score = calculate_severity_score(emergency_type=emergency_type, transcript=transcript)
    text = transcript.lower()
    if immediate_threat or any(cue in text for cue in _IMMEDIATE_REQUEST_CUES):
        score += 15
    score += min(max(0, people_at_risk), 4) * 5
    return clamp_score(score)


def calculate_help_required(*, emergency_type: EmergencyType, transcript: str) -> list[HelpRequired]:
    """Select services from type plus explicit transcript evidence only.

    This is decision support, not an autonomous dispatch instruction.  In
    particular, an accident does not imply an ambulance or fire service without
    injury, entrapment, or fire evidence.
    """
    text = transcript.lower()
    injured = any(cue in text for cue in _INJURY_CUES) and not any(cue in text for cue in _NO_INJURY_CUES)
    trapped = any(cue in text for cue in _TRAPPED_CUES)
    fire = any(cue in text for cue in _FIRE_CUES)
    help_required: list[HelpRequired] = []
    if emergency_type in {EmergencyType.POLICE, EmergencyType.WOMEN_SAFETY,
                          EmergencyType.DOMESTIC_VIOLENCE, EmergencyType.CHILD_SAFETY,
                          EmergencyType.ROBBERY, EmergencyType.ASSAULT, EmergencyType.HARASSMENT}:
        help_required.append(HelpRequired.POLICE)
    if emergency_type == EmergencyType.ACCIDENT:
        help_required.append(HelpRequired.POLICE)
    if emergency_type == EmergencyType.FIRE or fire:
        help_required.append(HelpRequired.FIRE_SERVICE)
    if emergency_type == EmergencyType.MEDICAL or any(cue in text for cue in _MEDICAL_CUES):
        help_required.extend([HelpRequired.AMBULANCE, HelpRequired.MEDICAL_ASSISTANCE])
    elif injured or trapped:
        help_required.append(HelpRequired.AMBULANCE)
    if trapped and emergency_type == EmergencyType.DISASTER:
        help_required.append(HelpRequired.RESCUE)
    if emergency_type == EmergencyType.DISASTER and not trapped:
        help_required.append(HelpRequired.MULTIPLE_SERVICES)
    if not help_required:
        return [HelpRequired.UNKNOWN]
    return list(dict.fromkeys(help_required))


def recommended_units_for_help(help_required: list[HelpRequired]) -> list[str]:
    """Derive visible unit recommendations from validated required services."""
    return [item.value for item in help_required if item not in {HelpRequired.UNKNOWN, HelpRequired.MULTIPLE_SERVICES}]
