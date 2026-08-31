from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证凭证无效或已过期", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = int(str(payload["sub"]))
        token_version = int(payload.get("ver", -1))
    except (ValueError, KeyError, jwt.InvalidTokenError, RuntimeError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != token_version:
        raise unauthorized
    return user
