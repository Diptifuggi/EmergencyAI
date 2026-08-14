from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import uuid

router = APIRouter(tags=["audit"])


def _get_current_user():
    return None


@router.get("/")
async def list_audit_logs(page: int = 1, page_size: int = 50, current_user=Depends(_get_current_user)):
    # generate sample logs
    items = []
    now = datetime.utcnow()
    for i in range(0, min(100, page_size)):
        t = (now - timedelta(minutes=i*5)).isoformat()
        items.append({
            "id": str(uuid.uuid4()),
            "time": t,
            "user": {"id": "u1", "full_name": "System Admin"},
            "action": i%5==0 and 'created' or 'updated',
            "entity_type": 'call',
            "entity_id": str(uuid.uuid4())
        })
    return {"items": items, "total": 100}
