from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from ..core.exceptions import OllamaUnavailableError, PipelineStepFailedError
from ..core.logger import get_logger
from ..schemas.emergency_analysis import (
    STATUS_ANALYSIS_FAILED,
    STATUS_ANALYZED,
    EmergencyAnalysis,
    EmergencyAnalysisInput,
    EmergencyAnalysisResult,
    EmergencyType,
    HelpRequired,
    AnalysisLevel,
    SUPPORTED_LANGUAGES,
    _RawEmergencyAnalysis,
)
from .analysis_normalizers import normalize_emergency_type
from .emergency_keywords import evidence
from .incident_rules import IncidentFacts, extract_incident_facts, services_for_facts
from .ollama_client import OllamaClient
from .scoring_policy import (
    calculate_priority_score_raw,
    calculate_help_required,
    clamp_score,
    level_for_score,
    calculate_severity_score,
    recommended_units_for_help,
    emergency_numbers_for_help,
)

logger = get_logger("app.services.emergency_analysis_service")


_TYPE_LABELS = {
    EmergencyType.CRIME_POLICE: "active crime or police-safety incident",
    EmergencyType.MEDICAL: "medical emergency",
    EmergencyType.POLICE: "police-assistance incident",
    EmergencyType.FIRE: "fire emergency",
    EmergencyType.ACCIDENT: "transport accident",
    EmergencyType.WOMEN_SAFETY: "women's safety incident",
    EmergencyType.DOMESTIC_VIOLENCE: "domestic-violence incident",
    EmergencyType.CHILD_SAFETY: "child-safety or missing-person incident",
    EmergencyType.CYBERCRIME: "cybercrime report",
    EmergencyType.LPG: "LPG or gas hazard",
    EmergencyType.ROBBERY: "robbery report",
    EmergencyType.ASSAULT: "assault report",
    EmergencyType.HARASSMENT: "harassment report",
    EmergencyType.DISASTER: "disaster or rescue incident",
    EmergencyType.OTHER: "other reported concern",
    EmergencyType.UNKNOWN: "unclassified report",
}


def _reported_evidence(facts: IncidentFacts) -> list[str]:
    evidence: list[str] = []
    if facts.victim_count_source == "default":
        evidence.append("at least 1 person assumed (no count stated)")
    for condition, label in (
        (facts.immediate_danger, "immediate danger"),
        (facts.injuries_present, "reported injuries"),
        (facts.severe_bleeding, "severe bleeding"),
        (facts.unconscious_person, "an unconscious person"),
        (facts.fire_present, "fire"),
        (facts.smoke_present, "smoke"),
        (facts.explosion_present, "an explosion"),
        (facts.trapped_persons, "trapped people"),
        (facts.weapon_present, "a reported weapon"),
        (facts.road_accident, "a road accident"),
        (facts.railway_incident, "a railway incident"),
        (facts.highway_incident, "a highway location"),
        (facts.domestic_violence, "domestic violence"),
        (facts.sexual_violence, "sexual violence"),
        (facts.missing_person, "a missing person"),
        (facts.cyber_crime, "suspected cybercrime"),
        (facts.lpg_leak, "an LPG/gas leak"),
        (facts.heavy_rain, "heavy rain"),
        (facts.flood_risk, "possible flood risk"),
        (facts.flood_confirmed, "reported flooding"),
    ):
        if condition:
            evidence.append(label)
    if facts.victim_count is not None and facts.victim_count_source != "default":
        qualifier = "about " if facts.victim_count_approximate else ""
        if facts.victim_count_source == "explicit":
            evidence.append(f"{qualifier}{facts.victim_count} explicitly reported people")
        else:
            evidence.append(f"{qualifier}{facts.victim_count} people estimated")
    if facts.emergency_keywords:
        evidence.extend(facts.emergency_keywords[:5])
    return list(dict.fromkeys(evidence))[:6]


def _incident_description(facts: IncidentFacts, emergency_type: EmergencyType) -> str:
    if facts.hypothetical:
        return "Caller asks about a hypothetical emergency; no current incident is established."
    label = _TYPE_LABELS[emergency_type]
    if facts.negated:
        return f"Caller explicitly negates evidence of a {label}; confirm if the situation has changed."
    if facts.historical:
        return f"Caller describes a past {label}; current danger is not established."
    if facts.resolved:
        return f"Caller reports a resolved {label}; confirm whether anyone still needs assistance."
    if facts.uncertain or facts.flood_risk:
        prefix = "Caller is uncertain about a possible" if facts.uncertain else "Caller reports a possible"
        details = _reported_evidence(facts)
        suffix = f"; reported evidence: {', '.join(details)}" if details else ""
        return f"{prefix} {label}{suffix}."
    if not facts.current_emergency:
        return f"The report describes a {facts.context_state} {label}; no current incident is established."
    if facts.sub_type == "self_harm_crisis":
        return "Caller reports a person in crisis; provide supportive assistance and operator review."
    details = _reported_evidence(facts)
    if details:
        return f"Caller reports a {label}; reported evidence: {', '.join(details)}."
    if emergency_type == EmergencyType.UNKNOWN:
        return "The report does not identify a supported incident type; operator clarification is required."
    return f"Caller reports a {label}; confirm details and current risk with the caller."


def _dispatch_reason(
    facts: IncidentFacts, emergency_type: EmergencyType, units: list[str]
) -> str:
    description = _incident_description(facts, emergency_type)
    if not facts.current_emergency:
        return f"{description} Do not infer a live dispatch need from this report alone."
    if units:
        return f"{description} Consider the listed units for dispatcher review; the report does not confirm dispatch."
    return (
        f"{description} No operational unit is mapped to the reported assistance; "
        "clarify the need with the caller."
    )


def _priority_reason(facts: IncidentFacts, priority_level: AnalysisLevel) -> str:
    reasons: list[str] = []
    if facts.immediate_danger:
        reasons.append("immediate danger")
    if facts.crime_in_progress:
        reasons.append("active crime in progress")
    if facts.weapon_present:
        reasons.append("weapon evidence")
    if facts.fire_present:
        reasons.append("fire or explosion evidence")
    if facts.trapped_persons:
        reasons.append("trapped persons")
    if facts.victim_count_source == "default":
        reasons.append("at least 1 person assumed (no count stated)")
    elif facts.victim_count is not None:
        qualifier = "explicitly reported" if facts.victim_count_source == "explicit" else "estimated"
        reasons.append(f"{facts.victim_count} {qualifier} people")
    if facts.injuries_present:
        reasons.append("explicit injury evidence")
    if facts.unconscious_person:
        reasons.append("reported unconscious person")
    if facts.severe_bleeding:
        reasons.append("reported severe bleeding")
    if facts.flood_confirmed:
        reasons.append("reported flooding")
    if facts.uncertain:
        reasons.append("uncertain incident details")
    if not facts.current_emergency:
        return (
            f"The report is {facts.context_state}; priority is {priority_level.value} "
            "because current dispatch urgency is not established."
        )
    if reasons:
        return f"{priority_level.value} priority reflects reported {', '.join(reasons)}."
    return (
        f"{priority_level.value} priority reflects the available incident evidence. "
        "No explicit immediate-danger indicator was detected; this is not a safety finding."
    )


def _dispatch_action(
    facts: IncidentFacts, priority_level: AnalysisLevel, units: list[str]
) -> str:
    if not facts.current_emergency:
        return (
            "Confirm whether the report describes a current incident before considering "
            "dispatch. Human operator confirmation is required."
        )
    if facts.uncertain:
        return (
            "Clarify whether the danger is current, who is affected, and the caller's "
            "location. Human operator confirmation is required before any dispatch."
        )
    if not units:
        return (
            "Clarify the assistance needed and consult local response procedures; no "
            "operational unit is configured for this service. Human operator confirmation "
            "is required."
        )
    return (
        f"Review at {priority_level.value} priority and consider the listed units after "
        "verifying the caller's location and circumstances. Human operator confirmation "
        "is required; no units have been assigned or dispatched by this system."
    )


SYSTEM_PROMPT = """You are EmergencyIQ, an emergency dispatch triage assistant.
Analyze ONLY the supplied emergency transcript text. Do not invent facts not present in the transcript.

Return JSON ONLY with exactly these keys (no extra keys):
{
    "emergency_type": "<one category or unknown>",
  "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "immediate_threat": <true|false>,
  "people_at_risk": <non-negative integer>,
    "victim_count": <non-negative integer or null>,
    "injuries_present": <true|false>,
    "unconscious_person": <true|false>,
    "severe_bleeding": <true|false>,
    "medical_emergency": <true|false>,
    "fire_present": <true|false>,
    "explosion_present": <true|false>,
    "trapped_persons": <true|false>,
    "rescue_required": <true|false>,
    "railway_incident": <true|false>,
    "road_accident": <true|false>,
    "highway_incident": <true|false>,
    "weapon_present": <true|false>,
    "child_involved": <true|false>,
    "elderly_involved": <true|false>,
    "domestic_violence": <true|false>,
    "crime_in_progress": <true|false>,
    "home_intrusion": <true|false>,
    "burglary_in_progress": <true|false>,
    "robbery_in_progress": <true|false>,
    "assault_in_progress": <true|false>,
    "police_required": <true|false>,
    "weapon_type": "<gun|knife|other|null>",
  "help_required": ["<zero or more help values>"],
  "emergency_keywords": ["<meaningful emergency phrases only>"],
  "priority_score": <integer 0-100>,
  "priority_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "panic_score": <integer 0-100>,
  "panic_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "stress_score": <integer 0-100>,
  "stress_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "dispatch_recommendation": {"recommended_units": ["<unit names>"]},
  "confidence": <float 0.0-1.0>
}

emergency_type MUST be one of:
crime_police, medical, police, fire, accident, women_safety, domestic_violence, child_safety,
robbery, assault, harassment, disaster, cybercrime, lpg, other, unknown

help_required values MUST be from:
police, ambulance, fire_service, rescue, medical_assistance, women_safety_support,
child_protection, multiple_services, unknown

The service and dispatch fields are legacy extraction hints only. Do not decide
final dispatch services or emergency numbers; the backend deterministic rule
engine makes that decision from validated transcript evidence.

dispatch_recommendation.recommended_units should use short unit names such as:
police, ambulance, fire_service, rescue, medical_assistance, women_safety_support, child_protection

Extract severity, immediate_threat and people_at_risk from evidence in the transcript.
The backend, not this model, calculates final priority_score and priority_level.
- severity: LOW, MEDIUM, HIGH or CRITICAL evidence assessment.
- immediate_threat: true only for an active/immediate danger.
- people_at_risk: number directly supported by the transcript; use 0 if unknown.
- priority_score and priority_level are legacy fields and are ignored by the backend.
- panic_score: textual distress only (e.g. "help", "save me", "scared", repeated urgency).
  NOT clinical diagnosis. NOT acoustic voice analysis.
- stress_score: transcript-based tension/urgency language only. NOT clinical diagnosis.

For non-emergency or low-urgency reports (e.g. lost wallet), use low scores and
emergency_type "other" or "unknown" with appropriate help_required (often empty or ["unknown"]).

Use "unknown" when the transcript does not support a confident classification.
confidence reflects how clearly the transcript supports your analysis.

Preserve the supplied language context; analyze the transcript in its language when possible.
Do not provide medical or psychological diagnoses.
"""

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class EmergencyAnalysisService:
    """Analyze emergency call transcript text via Ollama with strict JSON validation."""

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        self._ollama = ollama_client or OllamaClient()

    async def analyze(self, payload: EmergencyAnalysisInput) -> EmergencyAnalysisResult:
        transcript = payload.resolved_text()
        language = payload.resolved_language()
        logger.info(
            "Emergency analysis start language=%s call_type=%s text_length=%d",
            language,
            payload.call_type,
            len(transcript),
        )

        if not transcript:
            return self._failure(
                code="empty_transcript",
                message="No transcript text available for analysis",
            )

        if language not in SUPPORTED_LANGUAGES:
            return self._failure(
                code="unsupported_language",
                message=f"Language '{language}' is not supported for analysis",
            )

        user_prompt = self._build_user_prompt(
            transcript=transcript,
            language=language,
            call_type=payload.call_type,
        )

        try:
            raw_content = await self._ollama.generate_json(SYSTEM_PROMPT, user_prompt)
            logger.info(
                "Emergency analysis model response received content_length=%d",
                len(raw_content),
            )
        except OllamaUnavailableError as exc:
            logger.exception("Ollama unavailable during analysis: %s", exc.message)
            fallback = self._rules_only_fallback(transcript, language)
            if fallback is not None:
                logger.warning("Using deterministic rules-only analysis after Ollama failure")
                return fallback
            return self._failure(code="ollama_unavailable", message=exc.message)

        try:
            analysis = self._parse_and_validate(
                raw_content, transcript=transcript, language=language
            )
        except PipelineStepFailedError as exc:
            logger.exception("Analysis validation failed: %s", exc.message)
            fallback = self._rules_only_fallback(transcript, language)
            if fallback is not None:
                logger.warning("Using deterministic rules-only analysis after invalid model output")
                return fallback
            return self._failure(
                code="invalid_analysis_response",
                message=exc.message,
            )
        except Exception as exc:
            logger.exception("Unexpected analysis error: %s", exc)
            return self._failure(
                code="analysis_error",
                message="Emergency analysis failed unexpectedly",
            )

        return EmergencyAnalysisResult(
            success=True,
            analysis=analysis,
            suggested_status=STATUS_ANALYZED,
        )

    def _rules_only_fallback(
        self, transcript: str, language: str
    ) -> EmergencyAnalysisResult | None:
        """Return a safe deterministic result when model extraction is unavailable."""
        facts = extract_incident_facts(transcript, language)
        if facts.emergency_type == "unknown" and not facts.immediate_danger:
            return None
        payload = {
            "emergency_type": "unknown",
            "panic_score": 0,
            "stress_score": 0,
            "confidence": 0.0,
        }
        try:
            analysis = self._parse_and_validate(
                json.dumps(payload), transcript=transcript, language=language
            )
        except (PipelineStepFailedError, ValidationError, ValueError):
            return None
        return EmergencyAnalysisResult(
            success=True,
            analysis=analysis,
            suggested_status=STATUS_ANALYZED,
        )

    def _build_user_prompt(self, *, transcript: str, language: str, call_type: str) -> str:
        return (
            f"Language code: {language}\n"
            f"Call type: {call_type}\n"
            f"Transcript:\n{transcript}"
        )

    def _parse_and_validate(
        self, raw_content: str, *, transcript: str, language: str = "en"
    ) -> EmergencyAnalysis:
        parsed = self._load_json_object(raw_content)
        try:
            raw = _RawEmergencyAnalysis.model_validate(parsed)
        except ValidationError as exc:
            missing_or_invalid = "; ".join(
                f"{error.get('loc', ('unknown',))}: {error.get('type', 'invalid')}"
                for error in exc.errors()
            )
            raise PipelineStepFailedError(
                f"LLM analysis JSON does not match expected schema ({missing_or_invalid})"
            ) from exc
        logger.info(
            "Emergency analysis JSON parsed and raw schema validated keys=%s",
            ",".join(sorted(parsed)),
        )

        try:
            facts = extract_incident_facts(transcript, language)
            emergency_type = EmergencyType(facts.emergency_type)
            if emergency_type == EmergencyType.UNKNOWN and not facts.non_live_context:
                # Preserve useful legacy LLM classification for non-emergency
                # reports while keeping deterministic facts authoritative when
                # the transcript contains an actual incident.
                emergency_type = normalize_emergency_type(raw.emergency_type)
            help_required = services_for_facts(facts)
            validated_injuries = facts.injuries_present
            validated_trapped = facts.trapped_persons
            validated_fire = facts.fire_present
            validated_medical = facts.medical_emergency
            dispatch_units = recommended_units_for_help(help_required)
            severity_score = calculate_severity_score(
                emergency_type=emergency_type,
                transcript=transcript,
                language=language,
            )
            severity_level = level_for_score(severity_score)
            priority_score_raw = (
                calculate_priority_score_raw(
                    emergency_type=emergency_type,
                    immediate_threat=facts.immediate_danger,
                    # Do not use an LLM-invented count as a dispatch multiplier.
                    # A future extractor may populate this only from explicit text.
                    people_at_risk=0,
                    transcript=transcript,
                    language=language,
                    victim_count=facts.victim_count,
                    victim_count_source=facts.victim_count_source,
                    caller_request=facts.caller_request is not None,
                )
                if facts.current_emergency
                else None
            )
            priority_score = clamp_score(priority_score_raw) if priority_score_raw is not None else 0
            priority_level = level_for_score(priority_score)
            # There is no calibrated model probability or supported emotion
            # estimator, so those values are explicitly unavailable.
            confidence = None
            emergency_numbers = emergency_numbers_for_help(
                help_required,
                emergency_type=emergency_type,
                highway_incident=facts.highway_incident and facts.road_accident,
                railway_incident=facts.railway_incident
                and emergency_type == EmergencyType.ACCIDENT,
                serious=priority_score >= 51,
            )
            reason = _dispatch_reason(facts, emergency_type, dispatch_units)
            logger.info("[EmergencyIQ] Incident type detected: %s", emergency_type.value)
            logger.info("[EmergencyIQ] Priority calculated: %s", priority_level.value)
            logger.info("[EmergencyIQ] Police required: %s", facts.police_required)
            logger.info("[EmergencyIQ] Recommended units: %s", ", ".join(dispatch_units) or "none")
            logger.info("[EmergencyIQ] Emergency numbers: %s", ", ".join(emergency_numbers) or "none")
            return EmergencyAnalysis(
                emergency_type=emergency_type,
                severity=severity_level,
                sub_type=facts.sub_type,
                help_required=help_required,
                emergency_keywords=facts.emergency_keywords,
                priority_score=priority_score,
                priority_score_raw=priority_score_raw,
                priority_level=priority_level,
                panic_score=None,
                panic_level=None,
                stress_score=None,
                stress_level=None,
                dispatch_recommendation={
                    "recommended_units": dispatch_units,
                    "emergency_numbers": emergency_numbers,
                    "reason": reason,
                    "priority_reason": _priority_reason(
                        facts, priority_level
                    ),
                    "dispatcher_action": _dispatch_action(
                        facts, priority_level, dispatch_units
                    ),
                },
                confidence=confidence,
                human_confirmation_required=True,
                context_state=facts.context_state,
                current_emergency=facts.current_emergency,
                hypothetical=facts.hypothetical,
                historical=facts.historical,
                resolved=facts.resolved,
                uncertain=facts.uncertain,
                negated=facts.negated,
                victim_count=facts.victim_count,
                victim_count_approximate=facts.victim_count_approximate,
                victim_count_source=facts.victim_count_source,
                injuries_present=validated_injuries,
                unconscious_person=facts.unconscious_person,
                severe_bleeding=facts.severe_bleeding,
                medical_emergency=validated_medical,
                immediate_danger=facts.immediate_danger,
                fire_present=validated_fire,
                explosion_present=facts.explosion_present,
                trapped_persons=validated_trapped,
                rescue_required=validated_trapped,
                railway_incident=facts.railway_incident,
                road_accident=facts.road_accident,
                highway_incident=facts.highway_incident,
                weapon_present=facts.weapon_present,
                child_involved=facts.children_involved,
                elderly_involved=facts.elderly_involved,
                domestic_violence=facts.domestic_violence,
                crime_in_progress=facts.crime_in_progress,
                police_required=facts.police_required,
                sexual_violence=facts.sexual_violence,
                missing_person=facts.missing_person,
                burglary_in_progress=facts.burglary_in_progress,
                home_intrusion=facts.home_intrusion,
                robbery_in_progress=facts.robbery_in_progress,
                assault_in_progress=facts.assault_in_progress,
                smoke_present=facts.smoke_present,
                weapon_type=facts.weapon_type,
                children_involved=facts.children_involved,
                cyber_crime=facts.cyber_crime,
                lpg_leak=facts.lpg_leak,
                heavy_rain=facts.heavy_rain,
                flood_risk=facts.flood_risk,
                flood_confirmed=facts.flood_confirmed,
                location_description=facts.location_description,
                caller_request=facts.caller_request,
                recommended_units=dispatch_units,
                incident_description=_incident_description(facts, emergency_type),
            )
        except (ValueError, ValidationError) as exc:
            raise PipelineStepFailedError(
                "LLM analysis contains invalid enum or field values"
            ) from exc

    def _load_json_object(self, raw_content: str) -> dict[str, Any]:
        cleaned = _JSON_FENCE_RE.sub("", raw_content.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise PipelineStepFailedError(
                "LLM returned malformed JSON"
            ) from exc

        if not isinstance(data, dict):
            raise PipelineStepFailedError("LLM JSON root must be an object")

        return data

    def _failure(self, *, code: str, message: str) -> EmergencyAnalysisResult:
        return EmergencyAnalysisResult(
            success=False,
            failure_code=code,
            failure_message=message,
            suggested_status=STATUS_ANALYSIS_FAILED,
        )
