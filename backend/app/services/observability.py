import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.db_models import (
    OperationalEvent, SecurityEvent, AuthRateLimit, IdempotencyRecord
)


SLOW_REQUEST_MS=max(250,int(os.getenv('WAZEN_SLOW_REQUEST_MS','1500')))
RETENTION_DAYS=max(7,int(os.getenv('WAZEN_OPERATIONAL_RETENTION_DAYS','30')))


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def cleanup_operational_events(db: Session,now: datetime | None=None) -> int:
    now=now or _now()
    cutoff=now-timedelta(days=RETENTION_DAYS)
    result=db.execute(delete(OperationalEvent).where(OperationalEvent.created_at<cutoff))
    db.commit()
    return int(result.rowcount or 0)


def log_operational_event(
    db: Session,
    *,
    event_type: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: str | None=None,
    details: dict | None=None,
):
    cleanup_operational_events(db)
    row=OperationalEvent(
        event_type=event_type.upper(),
        method=method.upper()[:12],
        path=path[:255],
        status_code=int(status_code),
        duration_ms=round(float(duration_ms),2),
        request_id=(request_id[:80] if request_id else None),
        details_json=json.dumps(details or {},ensure_ascii=False,sort_keys=True,default=str),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_operational_events(
    db: Session,
    *,
    event_type: str | None=None,
    status_code: int | None=None,
    limit: int=100,
):
    stmt=select(OperationalEvent).order_by(OperationalEvent.created_at.desc())
    if event_type:
        stmt=stmt.where(OperationalEvent.event_type==event_type.upper())
    if status_code is not None:
        stmt=stmt.where(OperationalEvent.status_code==status_code)
    rows=db.scalars(stmt.limit(max(1,min(limit,500)))).all()
    return [{
        'id':x.id,
        'event_type':x.event_type,
        'method':x.method,
        'path':x.path,
        'status_code':x.status_code,
        'duration_ms':x.duration_ms,
        'request_id':x.request_id,
        'details':json.loads(x.details_json or '{}'),
        'created_at':x.created_at.isoformat(),
    } for x in rows]


def operations_summary(db: Session,readiness: dict) -> dict:
    now=_now()
    hour=now-timedelta(hours=1)
    day=now-timedelta(hours=24)

    recent_5xx=int(db.scalar(select(func.count(OperationalEvent.id)).where(
        OperationalEvent.event_type=='HTTP_5XX',
        OperationalEvent.created_at>=hour,
    )) or 0)
    slow_1h=int(db.scalar(select(func.count(OperationalEvent.id)).where(
        OperationalEvent.event_type=='SLOW_REQUEST',
        OperationalEvent.created_at>=hour,
    )) or 0)
    blocked_security_1h=int(db.scalar(select(func.count(SecurityEvent.id)).where(
        SecurityEvent.outcome=='BLOCKED',
        SecurityEvent.created_at>=hour,
    )) or 0)
    auth_blocks=int(db.scalar(select(func.count(AuthRateLimit.id)).where(
        AuthRateLimit.blocked_until.is_not(None),
        AuthRateLimit.blocked_until>now,
    )) or 0)
    pending_idempotency=int(db.scalar(select(func.count(IdempotencyRecord.id)).where(
        IdempotencyRecord.state=='PENDING',
    )) or 0)
    stale_cutoff=now-timedelta(seconds=max(30,int(os.getenv('WAZEN_IDEMPOTENCY_STALE_SECONDS','120'))))
    stale_idempotency=int(db.scalar(select(func.count(IdempotencyRecord.id)).where(
        IdempotencyRecord.state=='PENDING',
        IdempotencyRecord.created_at<=stale_cutoff,
    )) or 0)
    total_errors_24h=int(db.scalar(select(func.count(OperationalEvent.id)).where(
        OperationalEvent.event_type=='HTTP_5XX',
        OperationalEvent.created_at>=day,
    )) or 0)

    alerts=[]
    if not readiness.get('ready',False):
        alerts.append({'severity':'CRITICAL','code':'READINESS_FAILED','message':'One or more readiness checks are failing.'})
    if recent_5xx>=5:
        alerts.append({'severity':'CRITICAL','code':'HTTP_5XX_SPIKE','message':f'{recent_5xx} server errors in the last hour.'})
    elif recent_5xx>0:
        alerts.append({'severity':'WARNING','code':'HTTP_5XX_PRESENT','message':f'{recent_5xx} server errors in the last hour.'})
    if slow_1h>=10:
        alerts.append({'severity':'WARNING','code':'SLOW_REQUESTS','message':f'{slow_1h} slow requests in the last hour.'})
    if auth_blocks>=10:
        alerts.append({'severity':'WARNING','code':'AUTH_BLOCKS_HIGH','message':f'{auth_blocks} authentication subjects are currently blocked.'})
    if stale_idempotency>0:
        alerts.append({'severity':'WARNING','code':'STALE_IDEMPOTENCY','message':f'{stale_idempotency} idempotency claims are stale.'})

    return {
        'status':'ALERT' if alerts else 'OK',
        'readiness':readiness,
        'metrics':{
            'http_5xx_last_hour':recent_5xx,
            'http_5xx_last_24h':total_errors_24h,
            'slow_requests_last_hour':slow_1h,
            'security_blocks_last_hour':blocked_security_1h,
            'active_auth_blocks':auth_blocks,
            'pending_idempotency':pending_idempotency,
            'stale_idempotency':stale_idempotency,
        },
        'alerts':alerts,
        'generated_at':now.isoformat(),
    }
