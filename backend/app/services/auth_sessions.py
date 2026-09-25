import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import AuthSession, PasswordResetToken, User
from app.security import create_access_token, hash_password


REFRESH_DAYS = int(os.getenv('WAZEN_REFRESH_DAYS', '30'))
RESET_MINUTES = int(os.getenv('WAZEN_RESET_MINUTES', '30'))


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _raw_token() -> str:
    return secrets.token_urlsafe(48)


def issue_session(db: Session, user_id: str, rotated_from_id: str | None = None):
    raw = _raw_token()
    session = AuthSession(
        user_id=user_id,
        refresh_token_hash=token_hash(raw),
        expires_at=utcnow() + timedelta(days=REFRESH_DAYS),
        rotated_from_id=rotated_from_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        'access_token': create_access_token(user_id, minutes=30),
        'refresh_token': raw,
        'token_type': 'bearer',
        'access_expires_in': 1800,
        'refresh_expires_in': REFRESH_DAYS * 86400,
        'session_id': session.id,
    }


def rotate_session(db: Session, raw_refresh: str):
    now = utcnow()
    digest = token_hash(raw_refresh)
    session = db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == digest))
    if not session or session.revoked_at is not None or session.expires_at <= now:
        raise ValueError('INVALID_REFRESH_TOKEN')

    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise ValueError('INVALID_REFRESH_TOKEN')

    session.revoked_at = now
    db.commit()
    return issue_session(db, user.id, rotated_from_id=session.id)


def revoke_session(db: Session, raw_refresh: str, user_id: str | None = None):
    digest = token_hash(raw_refresh)
    session = db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == digest))
    if not session:
        return False
    if user_id and session.user_id != user_id:
        return False
    if session.revoked_at is None:
        session.revoked_at = utcnow()
        db.commit()
    return True


def revoke_all_sessions(db: Session, user_id: str):
    rows = db.scalars(select(AuthSession).where(
        AuthSession.user_id == user_id,
        AuthSession.revoked_at.is_(None),
    )).all()
    now = utcnow()
    for row in rows:
        row.revoked_at = now
    db.commit()
    return len(rows)


def create_password_reset(db: Session, user: User | None):
    # Always generate the same outward response to avoid account enumeration.
    if not user:
        return None
    raw = _raw_token()
    row = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash(raw),
        expires_at=utcnow() + timedelta(minutes=RESET_MINUTES),
    )
    db.add(row)
    db.commit()
    return raw


def consume_password_reset(db: Session, raw_token: str, new_password: str):
    digest = token_hash(raw_token)
    now = utcnow()
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == digest))
    if not row or row.used_at is not None or row.expires_at <= now:
        raise ValueError('INVALID_RESET_TOKEN')

    user = db.get(User, row.user_id)
    if not user or not user.active:
        raise ValueError('INVALID_RESET_TOKEN')

    user.password_hash = hash_password(new_password)
    row.used_at = now
    revoke_all_sessions(db, user.id)
    db.commit()
    return user



def list_active_sessions(db: Session, user_id: str):
    now=utcnow()
    rows=db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id==user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at>now,
        )
        .order_by(AuthSession.created_at.desc())
    ).all()
    return [{
        'id':x.id,
        'created_at':x.created_at.isoformat(),
        'expires_at':x.expires_at.isoformat(),
        'rotated_from_id':x.rotated_from_id,
    } for x in rows]
