from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.emergency_analysis import (
    STATUS_ANALYZED,
    STATUS_ANALYSIS_FAILED,
    AnalysisLevel,
    DispatchRecommendation,
    EmergencyAnalysis,
    EmergencyAnalysisResult,
    EmergencyType,
    HelpRequired,
)


def make_analysis_result(**overrides: Any) -> EmergencyAnalysisResult:
    analysis = EmergencyAnalysis(
        emergency_type=overrides.pop("emergency_type", EmergencyType.POLICE),
        help_required=overrides.pop("help_required", [HelpRequired.POLICE]),
        emergency_keywords=overrides.pop("emergency_keywords", ["police", "help"]),
        priority_score=overrides.pop("priority_score", 80),
        priority_level=overrides.pop("priority_level", AnalysisLevel.HIGH),
        panic_score=overrides.pop("panic_score", 60),
        panic_level=overrides.pop("panic_level", AnalysisLevel.MEDIUM),
        stress_score=overrides.pop("stress_score", 55),
        stress_level=overrides.pop("stress_level", AnalysisLevel.MEDIUM),
        dispatch_recommendation=overrides.pop(
            "dispatch_recommendation",
            DispatchRecommendation(recommended_units=["police"]),
        ),
        confidence=overrides.pop("confidence", 0.85),
    )
    return EmergencyAnalysisResult(
        success=True,
        analysis=analysis,
        suggested_status=STATUS_ANALYZED,
    )


def make_analysis_failure(
    code: str = "ollama_unavailable",
    message: str = "Ollama backend is unavailable",
) -> EmergencyAnalysisResult:
    return EmergencyAnalysisResult(
        success=False,
        failure_code=code,
        failure_message=message,
        suggested_status=STATUS_ANALYSIS_FAILED,
    )


@pytest.fixture
def mock_analysis_success():
    with patch(
        "app.services.emergency_call_analysis_runner.EmergencyAnalysisService.analyze",
        new_callable=AsyncMock,
        return_value=make_analysis_result(),
    ) as mocked:
        yield mocked


@pytest.fixture
def mock_analysis_failure():
    with patch(
        "app.services.emergency_call_analysis_runner.EmergencyAnalysisService.analyze",
        new_callable=AsyncMock,
        return_value=make_analysis_failure(),
    ) as mocked:
        yield mocked


def valid_ollama_json(**overrides: Any) -> str:
    payload = {
        "emergency_type": "police",
        "help_required": ["police"],
        "emergency_keywords": ["police", "following me"],
        "priority_score": 85,
        "priority_level": "HIGH",
        "panic_score": 65,
        "panic_level": "MEDIUM",
        "stress_score": 60,
        "stress_level": "MEDIUM",
        "dispatch_recommendation": {"recommended_units": ["police"]},
        "confidence": 0.88,
    }
    payload.update(overrides)
    return json.dumps(payload)
