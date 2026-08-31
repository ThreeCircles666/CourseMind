from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=f"{settings.api_prefix}/auth",
    )


def auth_response(user: User, response: Response) -> AuthResponse:
    settings.validate_auth_config()
    set_refresh_cookie(response, create_refresh_token(user.id, user.token_version))
    return AuthResponse(access_token=create_access_token(user.id, user.token_version), user=UserResponse.model_validate(user))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    user = User(username=payload.username, nickname=payload.nickname, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="用户名已存在")
    return auth_response(user, response)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.username == payload.username.strip().lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return auth_response(user, response)


@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="刷新凭证无效或已过期")
    try:
        payload = decode_token(token, "refresh")
        user = db.get(User, int(str(payload["sub"])))
        token_version = int(payload.get("ver", -1))
    except (ValueError, KeyError, jwt.InvalidTokenError, RuntimeError):
        raise HTTPException(status_code=401, detail="刷新凭证无效或已过期")
    if user is None or not user.is_active or user.token_version != token_version:
        raise HTTPException(status_code=401, detail="刷新凭证无效或已过期")
    return auth_response(user, response)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    current_user.token_version += 1
    db.commit()
    response.delete_cookie(settings.refresh_cookie_name, path=f"{settings.api_prefix}/auth")
