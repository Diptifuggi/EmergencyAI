from app.schemas.emergency_analysis import AnalysisLevel, EmergencyType, HelpRequired
from app.services.analysis_normalizers import (
    enrich_help_required,
    priority_level_to_db_value,
)


def test_priority_level_to_db_value() -> None:
    assert priority_level_to_db_value(AnalysisLevel.HIGH) == "high"
    assert priority_level_to_db_value(AnalysisLevel.CRITICAL) == "critical"


def test_enrich_help_required_replaces_unknown_with_transcript_hints() -> None:
    result = enrich_help_required(
        help_required=[HelpRequired.UNKNOWN],
        emergency_type=EmergencyType.POLICE,
        transcript="medical emergency near highway",
        dispatch_units=["police"],
    )

    assert HelpRequired.POLICE in result
    assert HelpRequired.MEDICAL_ASSISTANCE in result
    assert HelpRequired.UNKNOWN not in result
