from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from app.schemas.v1 import UserOut, UserCreate, UserUpdate
from datetime import datetime
import uuid

router = APIRouter(tags=["users"])


def _get_current_user():
    """Auth dependency placeholder."""
    return None


_FAKE_USERS = {}


@router.get("/", response_model=List[UserOut], status_code=status.HTTP_200_OK)
async def list_users(current_user=Depends(_get_current_user)):
    """Placeholder users listing."""
    return list(_FAKE_USERS.values())


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, current_user=Depends(_get_current_user)):
    uid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    user = {"id": uid, "full_name": payload.full_name, "email": payload.email, "phone": payload.phone, "username": payload.email.split('@')[0], "role_name": payload.role_name or 'Dispatcher', "is_active": payload.is_active, "created_at": now}
    _FAKE_USERS[uid] = user
    return user


@router.get("/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
async def get_user(user_id: str, current_user=Depends(_get_current_user)):
    user = _FAKE_USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail='Not found')
    return user


@router.patch("/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
async def update_user(user_id: str, payload: UserUpdate, current_user=Depends(_get_current_user)):
    user = _FAKE_USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail='Not found')
    for k, v in payload.dict(exclude_unset=True).items():
        user[k] = v
    _FAKE_USERS[user_id] = user
    return user
