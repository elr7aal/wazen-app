import os
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import EmailVerificationToken, User
from app.services.auth_sessions import token_hash, utcnow


VERIFY_MINUTES=max(10,int(os.getenv('WAZEN_EMAIL_VERIFY_MINUTES','60')))
RESEND_SECONDS=max(30,int(os.getenv('WAZEN_EMAIL_VERIFY_RESEND_SECONDS','60')))


def verification_resend_retry_after(db: Session,user_id: str) -> int:
    latest=db.scalar(
        select(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id==user_id,
            EmailVerificationToken.used_at.is_(None),
        )
        .order_by(EmailVerificationToken.created_at.desc())
        .limit(1)
    )
    if not latest:
        return 0
    elapsed=(utcnow()-latest.created_at).total_seconds()
    return max(0,int(RESEND_SECONDS-elapsed))


def create_email_verification(db: Session,user: User,*,replace_pending: bool=True):
    now=utcnow()
    if replace_pending:
        rows=db.scalars(select(EmailVerificationToken).where(
            EmailVerificationToken.user_id==user.id,
            EmailVerificationToken.used_at.is_(None),
        )).all()
        for row in rows:
            row.used_at=now
    raw=secrets.token_urlsafe(48)
    row=EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash(raw),
        expires_at=now+timedelta(minutes=VERIFY_MINUTES),
        created_at=now,
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
    rows=db.scalars(select(EmailVerificationToken).where(
        EmailVerificationToken.user_id==user.id,
        EmailVerificationToken.used_at.is_(None),
    )).all()
    for token in rows:
        token.used_at=now
    db.commit()
    db.refresh(user)
    return user
