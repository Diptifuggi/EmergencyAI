from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str

# Very small in-memory "DB"
_users: List[dict] = []
_next_id = 1

@router.post("/", response_model=UserOut)
async def create_user(payload: UserCreate):
    global _next_id
    for u in _users:
        if u["email"] == payload.email:
            raise HTTPException(status_code=409, detail="Email already exists")
    user = {"id": _next_id, "email": payload.email, "role": payload.role}
    _users.append(user)
    _next_id += 1
    return user

@router.get("/", response_model=List[UserOut])
async def list_users():
    return _users

@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int):
    for u in _users:
        if u["id"] == user_id:
            return u
    raise HTTPException(status_code=404, detail="User not found")
