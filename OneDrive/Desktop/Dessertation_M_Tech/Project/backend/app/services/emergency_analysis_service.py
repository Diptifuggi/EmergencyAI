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
    HelpRequired,
    SUPPORTED_LANGUAGES,
    _RawEmergencyAnalysis,
)
from .analysis_normalizers import normalize_emergency_type
from .ollama_client import OllamaClient
from .scoring_policy import (
    calculate_priority_score,
    calculate_help_required,
    clamp_score,
    level_for_score,
    calculate_severity_score,
    recommended_units_for_help,
)

logger = get_logger("app.services.emergency_analysis_service")

SYSTEM_PROMPT = """You are EmergencyIQ, an emergency dispatch triage assistant.
Analyze ONLY the supplied emergency transcript text. Do not invent facts not present in the transcript.

Return JSON ONLY with exactly these keys (no extra keys):
{
  "emergency_type": "<one category>",
  "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "immediate_threat": <true|false>,
  "people_at_risk": <non-negative integer>,
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
medical, police, fire, accident, women_safety, domestic_violence, child_safety,
robbery, assault, harassment, disaster, other, unknown

help_required values MUST be from:
police, ambulance, fire_service, rescue, medical_assistance, women_safety_support,
child_protection, multiple_services, unknown

Include ALL services implied by the transcript. Example: "medical emergency near highway"
should include medical_assistance (and often ambulance) even if emergency_type is police
or accident. Use multiple values when the transcript supports them.

Do NOT return help_required ["unknown"] when the transcript clearly mentions medical,
police, fire, ambulance, or other specific help needs.

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
        except OllamaUnavailableError as exc:
            logger.warning("Ollama unavailable during analysis: %s", exc.message)
            return self._failure(
                code="ollama_unavailable",
                message=exc.message,
            )

        try:
            analysis = self._parse_and_validate(raw_content, transcript=transcript)
        except PipelineStepFailedError as exc:
            logger.warning("Analysis validation failed: %s", exc.message)
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

    def _build_user_prompt(self, *, transcript: str, language: str, call_type: str) -> str:
        return (
            f"Language code: {language}\n"
            f"Call type: {call_type}\n"
            f"Transcript:\n{transcript}"
        )

    def _parse_and_validate(self, raw_content: str, *, transcript: str) -> EmergencyAnalysis:
        parsed = self._load_json_object(raw_content)
        try:
            raw = _RawEmergencyAnalysis.model_validate(parsed)
        except ValidationError as exc:
            raise PipelineStepFailedError(
                "LLM analysis JSON does not match expected schema"
            ) from exc

        try:
            emergency_type = normalize_emergency_type(raw.emergency_type)
            help_required = calculate_help_required(
                emergency_type=emergency_type, transcript=transcript
            )
            dispatch_units = recommended_units_for_help(help_required)
            priority_score = calculate_priority_score(
                emergency_type=emergency_type,
                immediate_threat=raw.immediate_threat,
                people_at_risk=raw.people_at_risk,
                transcript=transcript,
            )
            # These remain model-extracted textual indicators, but are bounded
            # and categorised by backend policy rather than LLM labels.
            panic_score = clamp_score(raw.panic_score)
            stress_score = clamp_score(raw.stress_score)

            return EmergencyAnalysis(
                emergency_type=emergency_type,
                severity=level_for_score(
                    calculate_severity_score(emergency_type=emergency_type, transcript=transcript)
                ),
                help_required=help_required,
                emergency_keywords=raw.emergency_keywords,
                priority_score=priority_score,
                priority_level=level_for_score(priority_score),
                panic_score=panic_score,
                panic_level=level_for_score(panic_score),
                stress_score=stress_score,
                stress_level=level_for_score(stress_score),
                dispatch_recommendation={
                    "recommended_units": dispatch_units,
                },
                confidence=min(max(float(raw.confidence), 0.0), 1.0),
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
