from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.logger import get_logger
from ...models.transcript import Transcript
from ...schemas.transcript import TranscriptCreate, TranscriptOut

router = APIRouter()
logger = get_logger("app.api.v1.transcripts")


@router.post("/", response_model=TranscriptOut, status_code=status.HTTP_201_CREATED)
async def create_transcript(
    payload: TranscriptCreate,
    db: AsyncSession = Depends(get_db),
) -> Transcript:
    """Persist one final transcript produced by the Flutter STT client."""
    transcript = Transcript(
        transcript_text=payload.transcript_text,
        language=payload.language,
        source=payload.source,
    )
    try:
        db.add(transcript)
        await db.commit()
        await db.refresh(transcript)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Unable to save STT transcript: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcript storage is temporarily unavailable",
        ) from exc

    return transcript


@router.get("/", response_model=list[TranscriptOut])
async def list_transcripts(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Transcript]:
    result = await db.execute(
        select(Transcript).order_by(Transcript.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())
