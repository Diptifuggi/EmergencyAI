from fastapi import APIRouter

from . import (
    health,
    auth,
    users,
    calls,
    incidents,
    uploads,
    transcripts,
    emergency_calls,
    stt,
    analytics,
    dashboard,
    roles,
    audit,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(calls.router, prefix="/calls", tags=["calls"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
api_router.include_router(emergency_calls.router, prefix="/emergency-calls", tags=["emergency-calls"])
api_router.include_router(stt.router, prefix="/stt", tags=["stt"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
