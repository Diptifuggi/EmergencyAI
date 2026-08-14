from fastapi import APIRouter

from . import health, auth, users, calls, incidents, uploads, transcripts, emergency_calls

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(calls.router, prefix="/calls", tags=["calls"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
api_router.include_router(emergency_calls.router, prefix="/emergency-calls", tags=["emergency-calls"])
