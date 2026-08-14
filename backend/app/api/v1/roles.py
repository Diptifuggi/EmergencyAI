from fastapi import APIRouter, Depends
from datetime import datetime

router = APIRouter(tags=["roles"])


def _get_current_user():
    return None


@router.get("/")
async def list_roles(current_user=Depends(_get_current_user)):
    now = datetime.utcnow().isoformat()
    roles = [
        {"name": "Admin", "description": "Full system access", "user_count": 1, "created_at": now},
        {"name": "Dispatcher", "description": "Handle incoming calls and dispatch units", "user_count": 3, "created_at": now},
        {"name": "Police", "description": "Police responders", "user_count": 5, "created_at": now},
        {"name": "Fire", "description": "Fire department", "user_count": 4, "created_at": now},
        {"name": "Ambulance", "description": "EMS responders", "user_count": 2, "created_at": now},
        {"name": "Analyst", "description": "Analytics and reporting", "user_count": 2, "created_at": now},
    ]
    return roles
