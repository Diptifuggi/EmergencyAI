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
    SUPPORTED_LANGUAGES,
    _RawEmergencyAnalysis,
)
from .analysis_normalizers import normalize_emergency_type
from .emergency_keywords import evidence
from .emergency_service_directory import emergency_contacts_for_services
from .incident_rules import extract_incident_facts, services_for_facts
from .ollama_client import OllamaClient
from .scoring_policy import (
    calculate_priority_score,
    calculate_help_required,
    clamp_score,
    level_for_score,
    calculate_severity_score,
    recommended_units_for_help,
    emergency_numbers_for_help,
)

logger = get_logger("app.services.emergency_analysis_service")


def _dispatch_reason(facts) -> str:
    if facts.burglary_in_progress:
        return "Caller reports an active home intrusion/burglary and requests police assistance."
    if facts.medical_emergency:
        return "Caller reports a medical emergency based on the provided information."
    if facts.fire_present:
        return "Caller reports fire or explosion evidence based on the provided information."
    if facts.road_accident:
        return "Caller reports a road accident based on the provided information."
    if facts.cyber_crime:
        return "Caller reports suspected online or cyber fraud based on the provided information."
    return "Based on the provided information, recommended units require human dispatcher confirmation."


def _priority_reason(facts) -> str:
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
    return "Priority based on " + ", ".join(reasons) + "." if reasons else "Limited explicit urgency evidence."

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
            logger.info(
                "Emergency analysis raw model response (truncated): %s",
                raw_content[:2000],
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
            if emergency_type == EmergencyType.UNKNOWN:
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
            priority_score = calculate_priority_score(
                emergency_type=emergency_type,
                immediate_threat=facts.immediate_danger,
                # Do not use an LLM-invented count as a dispatch multiplier.
                # A future extractor may populate this only from explicit text.
                people_at_risk=0,
                transcript=transcript,
                language=language,
            )
            priority_level = level_for_score(priority_score)
            confidence = min(0.95, 0.55 + 0.08 * sum(
                bool(value) for value in (
                    facts.police_required, facts.medical_emergency, facts.fire_present,
                    facts.home_intrusion, facts.road_accident, facts.cyber_crime,
                    facts.lpg_leak, facts.trapped_persons, facts.weapon_present,
                )
            ))
            if facts.burglary_in_progress or facts.home_intrusion:
                confidence = 0.90
            elif facts.medical_emergency or facts.fire_present or facts.road_accident:
                confidence = max(confidence, 0.82)
            emergency_numbers = emergency_contacts_for_services(
                [
                    "police" if item == HelpRequired.POLICE else
                    "ambulance" if item == HelpRequired.AMBULANCE else
                    "fire_service" if item == HelpRequired.FIRE_SERVICE else
                    "women_safety_support" if item == HelpRequired.WOMEN_SAFETY_SUPPORT else
                    "child_protection" if item == HelpRequired.CHILD_PROTECTION else
                    "cybercrime" if item == HelpRequired.CYBERCRIME else
                    "lpg" if item == HelpRequired.LPG else "rescue"
                    for item in help_required
                ],
                serious=priority_level in {level_for_score(51), level_for_score(76)},
            )
            if facts.railway_incident:
                emergency_numbers["139"] = "Railway Assistance"
            if facts.road_accident:
                emergency_numbers["1073"] = "Road Accident Assistance"
            if facts.elderly_involved:
                emergency_numbers["14567"] = "Senior Citizen Helpline"
            reason = _dispatch_reason(facts)
            logger.info("[EmergencyIQ] Incident type detected: %s", emergency_type.value)
            logger.info("[EmergencyIQ] Priority calculated: %s", priority_level.value)
            logger.info("[EmergencyIQ] Police required: %s", facts.police_required)
            logger.info("[EmergencyIQ] Recommended units: %s", ", ".join(dispatch_units) or "none")
            logger.info("[EmergencyIQ] Emergency numbers: %s", ", ".join(emergency_numbers) or "none")
            # These remain model-extracted textual indicators, but are bounded
            # and categorised by backend policy rather than LLM labels.
            panic_score = clamp_score(raw.panic_score)
            stress_score = clamp_score(raw.stress_score)

            return EmergencyAnalysis(
                emergency_type=emergency_type,
                severity=priority_level,
                sub_type=facts.sub_type,
                help_required=help_required,
                emergency_keywords=facts.emergency_keywords,
                priority_score=priority_score,
                priority_level=priority_level,
                panic_score=panic_score,
                panic_level=level_for_score(panic_score),
                stress_score=stress_score,
                stress_level=level_for_score(stress_score),
                dispatch_recommendation={
                    "recommended_units": dispatch_units,
                    "emergency_numbers": emergency_numbers,
                    "reason": reason,
                    "priority_reason": _priority_reason(facts),
                    "dispatcher_action": "AI recommendation - human dispatcher confirmation required. Verify caller location and dispatch appropriate resources.",
                },
                confidence=confidence,
                victim_count=facts.victim_count or raw.victim_count,
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
                caller_request=facts.caller_request,
                recommended_units=dispatch_units,
                incident_description=transcript,
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
