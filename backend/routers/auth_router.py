import re
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ACCESS_TOKEN_EXPIRE_MINUTES_REMEMBER,
    TOKEN_BLACKLIST,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from database import User, get_db
from rate_limit import limiter

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    confirm_password: str
    avatar_color: Optional[str] = "#6366f1"


class LoginRequest(BaseModel):
    username_or_email: str
    password: str
    remember_me: bool = False


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    avatar_color: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    password: str


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _validate_password(password: str) -> bool:
    return len(password) >= 8 and any(ch.isdigit() for ch in password)


@router.post("/auth/register")
@limiter.limit("5/hour")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if not re.fullmatch(r"^[A-Za-z0-9_]{3,20}$", username):
        raise HTTPException(status_code=400, detail="Username must be 3-20 chars (letters, numbers, underscore)")
    if not _validate_password(payload.password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 chars and include 1 number")
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    exists = db.query(User).filter(or_(User.username == username, User.email == payload.email)).first()
    if exists:
        if exists.username == username:
            raise HTTPException(status_code=409, detail="Username already exists")
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        username=username,
        email=payload.email,
        full_name=payload.full_name.strip() or username,
        hashed_password=get_password_hash(payload.password),
        avatar_color=payload.avatar_color or "#6366f1",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Registration successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
        },
    }


@router.post("/auth/login")
@limiter.limit("20/hour")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.username_or_email.strip()
    user = db.query(User).filter(or_(User.username == identifier, User.email == identifier)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    expiry_minutes = ACCESS_TOKEN_EXPIRE_MINUTES_REMEMBER if payload.remember_me else ACCESS_TOKEN_EXPIRE_MINUTES
    token = create_access_token({"sub": user.username}, expires_delta=timedelta(minutes=expiry_minutes))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "total_claims": user.total_claims,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "avatar_color": user.avatar_color,
        },
    }


@router.post("/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    token = _extract_bearer(authorization)
    if token:
        TOKEN_BLACKLIST.add(token)
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
def me(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    token = _extract_bearer(authorization)
    user = get_current_user(token, db) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "avatar_color": user.avatar_color,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "total_claims": user.total_claims,
    }


@router.put("/auth/profile")
def update_profile(
    payload: ProfileUpdateRequest,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    token = _extract_bearer(authorization)
    user = get_current_user(token, db) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip() or user.full_name
    if payload.avatar_color is not None:
        user.avatar_color = payload.avatar_color

    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_color": user.avatar_color,
        "total_claims": user.total_claims,
    }


@router.post("/auth/change-password")
def change_password(
    payload: ChangePasswordRequest,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    token = _extract_bearer(authorization)
    user = get_current_user(token, db) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if not _validate_password(payload.new_password):
        raise HTTPException(status_code=400, detail="New password must be at least 8 chars and include 1 number")

    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password changed"}


@router.delete("/auth/account")
def deactivate_account(
    payload: DeleteAccountRequest,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    token = _extract_bearer(authorization)
    user = get_current_user(token, db) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is incorrect")

    user.is_active = False
    db.commit()
    return {"message": "Account deactivated"}


@router.get("/auth/check-username")
def check_username(username: str, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == username).first() is not None
    return {"available": not exists}
