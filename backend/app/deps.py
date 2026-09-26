import os
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import User
from app.security import decode_access_token


bearer = HTTPBearer(auto_error=False)


def get_authenticated_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status_code=401, detail='Authentication required')
    try:
        user_id = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail='User not found or inactive')
    return user


def email_verification_enforced() -> bool:
    explicit=os.getenv('WAZEN_REQUIRE_EMAIL_VERIFIED')
    if explicit is not None:
        return explicit.strip().lower() in {'1','true','yes','on'}
    environment=os.getenv('WAZEN_ENV','development').strip().lower()
    return environment in {'production','prod'}


def get_current_user(
    user: User = Depends(get_authenticated_user),
) -> User:
    if email_verification_enforced() and not user.email_verified:
        raise HTTPException(status_code=403, detail='EMAIL_VERIFICATION_REQUIRED')
    return user
