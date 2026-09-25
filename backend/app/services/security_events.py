import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.db_models import SecurityEvent
from app.services.auth_rate_limit import subject_hash


RETENTION_DAYS=max(7,int(os.getenv('WAZEN_SECURITY_EVENT_RETENTION_DAYS','90')))


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def cleanup_security_events(db: Session,now: datetime | None=None) -> int:
    now=now or _now()
    cutoff=now-timedelta(days=RETENTION_DAYS)
    result=db.execute(delete(SecurityEvent).where(SecurityEvent.created_at<cutoff))
    db.commit()
    return int(result.rowcount or 0)


def log_security_event(
    db: Session,
    *,
    event_type: str,
    outcome: str,
    user_id: str | None=None,
    subject: str | None=None,
    client_host: str | None=None,
    request_id: str | None=None,
    details: dict | None=None,
):
    cleanup_security_events(db)
    row=SecurityEvent(
        event_type=event_type,
        outcome=outcome,
        user_id=user_id,
        subject_hash=subject_hash(subject) if subject else None,
        client_hash=subject_hash(client_host) if client_host else None,
        request_id=request_id,
        details_json=json.dumps(details or {},ensure_ascii=False,sort_keys=True,default=str),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_security_events(
    db: Session,
    *,
    event_type: str | None=None,
    outcome: str | None=None,
    limit: int=100,
):
    stmt=select(SecurityEvent).order_by(SecurityEvent.created_at.desc())
    if event_type:
        stmt=stmt.where(SecurityEvent.event_type==event_type.upper())
    if outcome:
        stmt=stmt.where(SecurityEvent.outcome==outcome.upper())
    rows=db.scalars(stmt.limit(max(1,min(limit,500)))).all()
    return [{
        'id':x.id,
        'event_type':x.event_type,
        'outcome':x.outcome,
        'user_id':x.user_id,
        'subject_hash':x.subject_hash,
        'client_hash':x.client_hash,
        'request_id':x.request_id,
        'details':json.loads(x.details_json or '{}'),
        'created_at':x.created_at.isoformat(),
    } for x in rows]
