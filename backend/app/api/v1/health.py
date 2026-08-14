# from fastapi import APIRouter, Depends, status
# from fastapi.responses import JSONResponse
# from sqlalchemy import text

# from app.core.database import get_db

# router = APIRouter()


# @router.get("/health",
#             response_model=None,
#             status_code=status.HTTP_200_OK)
# async def health():
#     return {"status": "ok"}


# @router.get("/health/db", status_code=status.HTTP_200_OK)
# async def health_db(db=Depends(get_db)):
#     try:
#         # get_db yields an AsyncSession
#         result = await db.execute(text("SELECT 1"))
#         _ = result.scalar()
#         return {"status": "ok", "db": "connected"}
#     except Exception:
#         return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": True, "message": "Database not reachable"})
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}


@router.get("/db", status_code=status.HTTP_200_OK)
async def health_db(db=Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        _ = result.scalar()
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": True, "message": "Database not reachable"})