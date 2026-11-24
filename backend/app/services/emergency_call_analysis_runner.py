from __future__ import annotations

import time
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import async_session
from ..core.logger import get_logger
from ..models.emergency_call import EmergencyCall
from ..schemas.emergency_analysis import (
    STATUS_ANALYZED,
    STATUS_ANALYSIS_FAILED,
    STATUS_ANALYZING,
    EmergencyAnalysisInput,
    EmergencyAnalysisResult,
)
from .analysis_normalizers import priority_level_to_db_value
from .emergency_analysis_service import EmergencyAnalysisService

logger = get_logger("app.services.emergency_call_analysis_runner")


async def _mark_analysis_failed(
    emergency_id: uuid.UUID,
    *,
    code: str,
    message: str,
) -> None:
    """Persist a terminal failure when the normal analysis task exits unexpectedly."""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(EmergencyCall)
                .where(EmergencyCall.id == emergency_id)
                .with_for_update()
            )
            emergency = result.scalar_one_or_none()
            if emergency is None or emergency.status != STATUS_ANALYZING:
                return
            metadata = dict(emergency.client_metadata or {})
            metadata["emergency_analysis_error"] = {
                "code": code,
                "message": message,
            }
            emergency.client_metadata = metadata
            emergency.status = STATUS_ANALYSIS_FAILED
            await db.commit()
    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to persist terminal analysis failure emergency_id=%s error_type=%s",
            emergency_id,
            type(exc).__name__,
        )


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
    logger.info("Emergency analysis status=analyzing emergency_id=%s", emergency.id)

    try:
        await db.commit()
        await db.refresh(emergency)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.warning(
            "Failed to persist analyzing status emergency_id=%s error_type=%s",
            emergency.id,
            type(exc).__name__,
        )
        if emergency.id is not None:
            await _mark_analysis_failed(
                emergency.id,
                code="analysis_persistence_failed",
                message="Emergency analysis could not be started",
            )
            persisted = await db.get(EmergencyCall, emergency.id)
            if persisted is not None:
                return persisted
        return emergency

    try:
        result = await service.analyze(build_analysis_input(emergency))
    except Exception as exc:
        logger.exception(
            "Emergency analysis raised unexpectedly emergency_id=%s error_type=%s",
            emergency.id,
            type(exc).__name__,
        )
        result = EmergencyAnalysisResult(
            success=False,
            failure_code="analysis_error",
            failure_message="Emergency analysis failed unexpectedly",
            suggested_status=STATUS_ANALYSIS_FAILED,
        )
    logger.info(
        "Emergency analysis completed emergency_id=%s success=%s failure_code=%s",
        emergency.id,
        result.success,
        result.failure_code,
    )
    if result.success and result.analysis is None:
        logger.error(
            "Emergency analysis returned success without an analysis emergency_id=%s",
            emergency.id,
        )
        result = EmergencyAnalysisResult(
            success=False,
            failure_code="invalid_analysis_result",
            failure_message="Emergency analysis did not produce a valid result",
            suggested_status=STATUS_ANALYSIS_FAILED,
        )

    if emergency.id is not None:
        try:
            query_result = await db.execute(
                select(EmergencyCall)
                .where(EmergencyCall.id == emergency.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            locked_emergency = query_result.scalar_one_or_none()
            if locked_emergency is None:
                return emergency
            emergency = locked_emergency
        except SQLAlchemyError as exc:
            await db.rollback()
            logger.exception(
                "Failed to refresh emergency metadata before analysis update emergency_id=%s error_type=%s",
                emergency.id,
                type(exc).__name__,
            )
            await _mark_analysis_failed(
                emergency.id,
                code="analysis_persistence_failed",
                message="Emergency analysis could not be persisted",
            )
            persisted = await db.get(EmergencyCall, emergency.id)
            return persisted or emergency

    emergency.client_metadata = result.to_client_metadata_patch(emergency.client_metadata)
    if result.success and result.analysis is not None:
        emergency.status = result.suggested_status or STATUS_ANALYZED
        emergency.priority = priority_level_to_db_value(result.analysis.priority_level)
    else:
        emergency.status = result.suggested_status or STATUS_ANALYSIS_FAILED

    try:
        await db.commit()
        await db.refresh(emergency)
        logger.info(
            "Emergency analysis database update complete emergency_id=%s status=%s",
            emergency.id,
            emergency.status,
        )
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error(
            "Failed to persist analysis outcome emergency_id=%s error_type=%s",
            emergency.id,
            type(exc).__name__,
        )
        if emergency.id is not None:
            await _mark_analysis_failed(
                emergency.id,
                code="analysis_persistence_failed",
                message="Emergency analysis could not be persisted",
            )
            persisted = await db.get(EmergencyCall, emergency.id)
            if persisted is not None:
                return persisted

    return emergency


async def run_post_create_analysis_in_background(emergency_id: uuid.UUID) -> None:
    """Analyze a persisted emergency using a session independent of the request."""
    started_at = time.perf_counter()
    try:
        async with async_session() as db:
            emergency = await db.get(EmergencyCall, emergency_id)
            if emergency is None:
                logger.warning(
                    "Background analysis skipped; emergency not found emergency_id=%s",
                    emergency_id,
                )
                return
            await run_post_create_analysis(db, emergency)
    except Exception:
        logger.exception(
            "Background emergency analysis failed emergency_id=%s",
            emergency_id,
        )
        await _mark_analysis_failed(
            emergency_id,
            code="analysis_error",
            message="Emergency analysis failed unexpectedly",
        )
    finally:
        logger.info(
            "Background emergency analysis finished emergency_id=%s elapsed_ms=%.1f",
            emergency_id,
            (time.perf_counter() - started_at) * 1000,
        )
