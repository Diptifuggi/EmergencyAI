from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from ...core.security import create_access_token, create_refresh_token, verify_password, hash_password

router = APIRouter()

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str
    password: str

# Temporary in-memory user store for initial foundation
_fake_user = {
    "id": 1,
    "email": "admin@emergencyiq.local",
    "password_hash": hash_password("changeme"),
    "role": "admin",
    "is_active": True,
}

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    if payload.email.lower() != _fake_user["email"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, _fake_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not _fake_user.get("is_active", False):
        raise HTTPException(status_code=403, detail="User inactive")

    access = create_access_token({"sub": str(_fake_user["id"]), "role": _fake_user["role"]})
    refresh = create_refresh_token({"sub": str(_fake_user["id"])})
    return {"access_token": access, "refresh_token": refresh}

@router.post("/refresh", response_model=TokenResponse)
async def refresh(token: str):
    # decode and re-issue access token
    from ...core.security import decode_token
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    # in real world fetch user and verify
    access = create_access_token({"sub": str(user_id), "role": "user"})
    refresh = create_refresh_token({"sub": str(user_id)})
    return {"access_token": access, "refresh_token": refresh}
