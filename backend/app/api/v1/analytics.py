from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def analytics_root():
    # Minimal analytics placeholder
    return {"status": "ok", "message": "analytics endpoint placeholder"}
