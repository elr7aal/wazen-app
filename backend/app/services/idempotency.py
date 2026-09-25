import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import IdempotencyRecord


STALE_SECONDS=max(30,int(os.getenv('WAZEN_IDEMPOTENCY_STALE_SECONDS','120')))
RETENTION_HOURS=max(1,int(os.getenv('WAZEN_IDEMPOTENCY_RETENTION_HOURS','168')))


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _payload_hash(payload: Any) -> str:
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def cleanup_idempotency_records(db: Session, now: datetime | None=None) -> int:
    now=now or _now()
    cutoff=now-timedelta(hours=RETENTION_HOURS)
    result=db.execute(delete(IdempotencyRecord).where(
        IdempotencyRecord.state=='COMPLETED',
        IdempotencyRecord.completed_at.is_not(None),
        IdempotencyRecord.completed_at<cutoff,
    ))
    db.commit()
    return int(result.rowcount or 0)


def _lookup(db: Session,user_id: str,method: str,path: str,key: str):
    return db.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.user_id==user_id,
            IdempotencyRecord.method==method,
            IdempotencyRecord.path==path,
            IdempotencyRecord.idempotency_key==key,
        )
        .with_for_update()
    )


def _handle_existing(db: Session,existing: IdempotencyRecord,digest: str,now: datetime):
    if existing.request_hash!=digest:
        raise ValueError('IDEMPOTENCY_PAYLOAD_CONFLICT')

    if existing.state=='COMPLETED' and existing.response_json:
        return {'mode':'REPLAY','record':existing,'response':json.loads(existing.response_json)}

    stale_before=now-timedelta(seconds=STALE_SECONDS)
    if existing.state=='PENDING' and existing.created_at<=stale_before:
        existing.created_at=now
        existing.completed_at=None
        existing.response_json=None
        db.commit()
        db.refresh(existing)
        return {'mode':'CLAIM','record':existing,'recovered':True}

    raise ValueError('IDEMPOTENCY_IN_PROGRESS')


def begin_idempotent(
    db: Session,
    *,
    user_id: str,
    method: str,
    path: str,
    key: str | None,
    payload: Any,
):
    if not key:
        return {'mode':'BYPASS','record':None}
    key=key.strip()
    if not key or len(key)>120:
        raise ValueError('INVALID_IDEMPOTENCY_KEY')

    now=_now()
    cleanup_idempotency_records(db,now)
    digest=_payload_hash(payload)
    existing=_lookup(db,user_id,method,path,key)
    if existing:
        return _handle_existing(db,existing,digest,now)

    row=IdempotencyRecord(
        user_id=user_id,
        method=method,
        path=path,
        idempotency_key=key,
        request_hash=digest,
        state='PENDING',
        created_at=now,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing=_lookup(db,user_id,method,path,key)
        if existing:
            return _handle_existing(db,existing,digest,now)
        raise ValueError('IDEMPOTENCY_IN_PROGRESS')

    db.refresh(row)
    return {'mode':'CLAIM','record':row}


def finish_idempotent(db: Session, record: IdempotencyRecord | None, response: dict):
    if record is None:
        return
    row=db.get(IdempotencyRecord,record.id)
    if not row:
        return
    row.state='COMPLETED'
    row.response_json=json.dumps(response,ensure_ascii=False,sort_keys=True,default=str)
    row.completed_at=_now()
    db.commit()


def abandon_idempotent(db: Session, record: IdempotencyRecord | None):
    if record is None:
        return
    row=db.get(IdempotencyRecord,record.id)
    if row and row.state=='PENDING':
        db.delete(row)
        db.commit()
