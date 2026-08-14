from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import get_logger
from ..models.emergency_call import EmergencyCall
from ..schemas.emergency_analysis import (
    STATUS_ANALYZING,
    EmergencyAnalysisInput,
)
from .analysis_normalizers import priority_level_to_db_value
from .emergency_analysis_service import EmergencyAnalysisService

logger = get_logger("app.services.emergency_call_analysis_runner")


def build_analysis_input(emergency: EmergencyCall) -> EmergencyAnalysisInput:
    return EmergencyAnalysisInput(
        text_content=emergency.text_content,
        transcription=emergency.transcription,
        language=emergency.language,
        call_type=emergency.call_type,
    )


def has_analyzable_transcript(emergency: EmergencyCall) -> bool:
    return bool(build_analysis_input(emergency).resolved_text())


async def run_post_create_analysis(
    db: AsyncSession,
    emergency: EmergencyCall,
    *,
    analysis_service: EmergencyAnalysisService | None = None,
) -> EmergencyCall:
    """
    Run EmergencyAnalysisService after the emergency call has been committed.

    The call is never deleted on analysis failure. Metadata and status are updated
    in a separate commit when analysis completes or fails controllably.
    """
    if not has_analyzable_transcript(emergency):
        return emergency

    service = analysis_service or EmergencyAnalysisService()
    emergency.status = STATUS_ANALYZING

    try:
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.warning(
            "Failed to persist analyzing status for emergency %s: %s",
            emergency.id,
            exc,
        )
        if emergency.id is not None:
            persisted = await db.get(EmergencyCall, emergency.id)
            if persisted is not None:
                return persisted
        return emergency

    result = await service.analyze(build_analysis_input(emergency))
    emergency.client_metadata = result.to_client_metadata_patch(emergency.client_metadata)
    if result.suggested_status:
        emergency.status = result.suggested_status
    if result.success and result.analysis is not None:
        emergency.priority = priority_level_to_db_value(result.analysis.priority_level)

    try:
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception(
            "Failed to persist analysis outcome for emergency %s: %s",
            emergency.id,
            exc,
        )
        if emergency.id is not None:
            persisted = await db.get(EmergencyCall, emergency.id)
            if persisted is not None:
                return persisted

    return emergency
