from fastapi import APIRouter, Depends
from datetime import datetime
from ...core.dependencies import get_current_admin
from ...schemas.v1 import UserOut

router = APIRouter(tags=["roles"])


@router.get("/")
async def list_roles(current_user: UserOut = Depends(get_current_admin)):
    now = datetime.utcnow().isoformat()
    roles = [
        {"name": "Admin", "description": "Full system access", "user_count": 1, "created_at": now},
        {"name": "Supervisor", "description": "Supervise dispatchers and incidents", "user_count": 1, "created_at": now},
        {"name": "Operator", "description": "Handle incoming calls, SOS alerts and dispatch units", "user_count": 3, "created_at": now},
        {"name": "User", "description": "Citizen mobile app user", "user_count": 0, "created_at": now},
    ]
    return roles
