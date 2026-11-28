from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.dependencies import get_current_admin
from ...models.auth_token import AuditLog
from ...schemas.v1 import UserOut

router = APIRouter(tags=["audit"])


def record_audit_log(
    db: AsyncSession,
    actor: Optional[UserOut],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            actor_username=actor.username if actor else None,
            actor_role=actor.role_name if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )


@router.get("/")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    current_user: UserOut = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    items = [
        {
            "id": str(row.id),
            "time": row.created_at.isoformat() if row.created_at else None,
            "user": {
                "id": str(row.actor_id) if row.actor_id else None,
                "full_name": row.actor_username or "System",
                "role": row.actor_role,
            },
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "details": row.details,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
