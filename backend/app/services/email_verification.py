import os
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import EmailVerificationToken, User
from app.services.auth_sessions import token_hash, utcnow


VERIFY_MINUTES=max(10,int(os.getenv('WAZEN_EMAIL_VERIFY_MINUTES','60')))


def create_email_verification(db: Session,user: User):
    raw=secrets.token_urlsafe(48)
    row=EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash(raw),
        expires_at=utcnow()+timedelta(minutes=VERIFY_MINUTES),
    )
    db.add(row)
    db.commit()
    return raw


def consume_email_verification(db: Session,raw_token: str):
    digest=token_hash(raw_token)
    now=utcnow()
    row=db.scalar(select(EmailVerificationToken).where(
        EmailVerificationToken.token_hash==digest
    ))
    if not row or row.used_at is not None or row.expires_at<=now:
        raise ValueError('INVALID_VERIFICATION_TOKEN')
    user=db.get(User,row.user_id)
    if not user or not user.active:
        raise ValueError('INVALID_VERIFICATION_TOKEN')
    user.email_verified=True
    user.email_verified_at=now
    row.used_at=now
    db.commit()
    db.refresh(user)
    return user


def mark_existing_email_verified(db: Session,user: User):
    if user.email_verified:
        return user
    user.email_verified=True
    user.email_verified_at=utcnow()
    db.commit()
    db.refresh(user)
    return user
