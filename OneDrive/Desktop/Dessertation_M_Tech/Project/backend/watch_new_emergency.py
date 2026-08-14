import asyncio
from datetime import datetime, timezone

from sqlalchemy import text

from app.core.database import engine


async def snapshot() -> dict:
    async with engine.connect() as conn:
        total = (
            await conn.execute(text("SELECT COUNT(*) FROM emergency_calls"))
        ).scalar_one()
        latest = (
            await conn.execute(
                text(
                    """
                    SELECT id::text, call_type, status,
                           left(coalesce(transcription, text_content, ''), 120) AS text,
                           original_audio_filename, audio_file_size,
                           created_at
                    FROM emergency_calls
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
            )
        ).mappings().first()
    return {"total": int(total), "latest": dict(latest) if latest else None}


async def main() -> None:
    before = await snapshot()
    print("BEFORE_TOTAL", before["total"])
    if before["latest"]:
        print("BEFORE_LATEST", before["latest"])

    print("WAITING_FOR_NEW_ROW ... speak on phone, then submit Voice+Text")
    start = datetime.now(timezone.utc)
    seen_id = before["latest"]["id"] if before["latest"] else None

    for i in range(120):  # ~4 minutes
        await asyncio.sleep(2)
        after = await snapshot()
        latest = after["latest"]
        if latest and latest["id"] != seen_id:
            print("STORED_YES")
            print("NEW_TOTAL", after["total"])
            print("NEW_RECORD", latest)
            has_audio = bool(latest.get("original_audio_filename") or latest.get("audio_file_size"))
            has_text = bool((latest.get("text") or "").strip())
            print("HAS_AUDIO", has_audio)
            print("HAS_TEXT", has_text)
            return
        if i % 5 == 0:
            print(f"still waiting... ({(i+1)*2}s) total={after['total']}")

    print("STORED_NO timeout — no new emergency_calls row detected")


if __name__ == "__main__":
    asyncio.run(main())
