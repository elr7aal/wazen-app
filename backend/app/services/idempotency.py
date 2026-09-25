import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import IdempotencyRecord


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _payload_hash(payload: Any) -> str:
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


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

    digest=_payload_hash(payload)
    existing=db.scalar(select(IdempotencyRecord).where(
        IdempotencyRecord.user_id==user_id,
        IdempotencyRecord.method==method,
        IdempotencyRecord.path==path,
        IdempotencyRecord.idempotency_key==key,
    ))
    if existing:
        if existing.request_hash!=digest:
            raise ValueError('IDEMPOTENCY_PAYLOAD_CONFLICT')
        if existing.state=='COMPLETED' and existing.response_json:
            return {'mode':'REPLAY','record':existing,'response':json.loads(existing.response_json)}
        raise ValueError('IDEMPOTENCY_IN_PROGRESS')

    row=IdempotencyRecord(
        user_id=user_id,
        method=method,
        path=path,
        idempotency_key=key,
        request_hash=digest,
        state='PENDING',
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing=db.scalar(select(IdempotencyRecord).where(
            IdempotencyRecord.user_id==user_id,
            IdempotencyRecord.method==method,
            IdempotencyRecord.path==path,
            IdempotencyRecord.idempotency_key==key,
        ))
        if existing and existing.request_hash==digest and existing.state=='COMPLETED' and existing.response_json:
            return {'mode':'REPLAY','record':existing,'response':json.loads(existing.response_json)}
        if existing and existing.request_hash!=digest:
            raise ValueError('IDEMPOTENCY_PAYLOAD_CONFLICT')
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
