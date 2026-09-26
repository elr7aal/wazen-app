import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.db_models import AuthRateLimit


WINDOW_SECONDS=max(60,int(os.getenv('WAZEN_AUTH_RATE_WINDOW_SECONDS','900')))
LOGIN_EMAIL_LIMIT=max(3,int(os.getenv('WAZEN_LOGIN_EMAIL_LIMIT','5')))
LOGIN_IP_LIMIT=max(20,int(os.getenv('WAZEN_LOGIN_IP_LIMIT','60')))
RESET_EMAIL_LIMIT=max(2,int(os.getenv('WAZEN_RESET_EMAIL_LIMIT','5')))
RESET_IP_LIMIT=max(20,int(os.getenv('WAZEN_RESET_IP_LIMIT','60')))
BLOCK_SECONDS=max(60,int(os.getenv('WAZEN_AUTH_BLOCK_SECONDS','900')))
RETENTION_HOURS=max(1,int(os.getenv('WAZEN_AUTH_RATE_RETENTION_HOURS','48')))


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    retry_after: int = 0


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _secret() -> bytes:
    value=(
        os.getenv('WAZEN_THROTTLE_SECRET')
        or os.getenv('JWT_SECRET')
        or os.getenv('WAZEN_SECRET')
        or 'wazen-dev-throttle-secret'
    )
    return value.encode('utf-8')


def subject_hash(value: str) -> str:
    normalized=(value or '').strip().lower()
    return hmac.new(_secret(),normalized.encode('utf-8'),hashlib.sha256).hexdigest()


def _row(db: Session,scope: str,subject: str):
    digest=subject_hash(subject)
    return db.scalar(
        select(AuthRateLimit)
        .where(AuthRateLimit.scope==scope,AuthRateLimit.subject_hash==digest)
        .with_for_update()
    ),digest


def cleanup_rate_limits(db: Session,now: datetime | None=None) -> int:
    now=now or _now()
    cutoff=now-timedelta(hours=RETENTION_HOURS)
    result=db.execute(delete(AuthRateLimit).where(
        AuthRateLimit.updated_at<cutoff,
        (AuthRateLimit.blocked_until.is_(None)) | (AuthRateLimit.blocked_until<now),
    ))
    db.commit()
    return int(result.rowcount or 0)


def check_allowed(db: Session,scope: str,subject: str,now: datetime | None=None) -> RateDecision:
    now=now or _now()
    row,_=_row(db,scope,subject)
    if not row:
        return RateDecision(True,0)
    if row.blocked_until and row.blocked_until>now:
        retry=max(1,int((row.blocked_until-now).total_seconds()))
        return RateDecision(False,retry)
    return RateDecision(True,0)


def record_failure(
    db: Session,
    *,
    scope: str,
    subject: str,
    limit: int,
    now: datetime | None=None,
) -> RateDecision:
    now=now or _now()
    row,digest=_row(db,scope,subject)
    if not row:
        row=AuthRateLimit(
            scope=scope,
            subject_hash=digest,
            attempts=0,
            window_started_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()

    if row.blocked_until and row.blocked_until>now:
        retry=max(1,int((row.blocked_until-now).total_seconds()))
        db.commit()
        return RateDecision(False,retry)

    if (now-row.window_started_at).total_seconds()>=WINDOW_SECONDS:
        row.attempts=0
        row.window_started_at=now
        row.blocked_until=None

    row.attempts+=1
    row.updated_at=now
    if row.attempts>=limit:
        row.blocked_until=now+timedelta(seconds=BLOCK_SECONDS)
    db.commit()

    if row.blocked_until and row.blocked_until>now:
        return RateDecision(False,BLOCK_SECONDS)
    return RateDecision(True,0)


def clear_subject(db: Session,scope: str,subject: str):
    digest=subject_hash(subject)
    db.execute(delete(AuthRateLimit).where(
        AuthRateLimit.scope==scope,
        AuthRateLimit.subject_hash==digest,
    ))
    db.commit()


def login_rate_keys(email: str,client_host: str | None):
    host=(client_host or 'unknown').strip().lower()
    return (
        ('LOGIN_EMAIL',email.strip().lower(),LOGIN_EMAIL_LIMIT),
        ('LOGIN_IP',host,LOGIN_IP_LIMIT),
    )


def reset_rate_keys(email: str,client_host: str | None):
    host=(client_host or 'unknown').strip().lower()
    return (
        ('RESET_EMAIL',email.strip().lower(),RESET_EMAIL_LIMIT),
        ('RESET_IP',host,RESET_IP_LIMIT),
    )
