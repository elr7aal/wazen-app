import importlib
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.db_models import AuthRateLimit, IdempotencyRecord, OperationalEvent
from app.services.auth_rate_limit import subject_hash
from app.services.idempotency import _payload_hash
from app.services.observability import log_operational_event

client=TestClient(app)
safe_client=TestClient(app,raise_server_exceptions=False)


def _admin_headers():
    return {
        'X-WAZEN-ADMIN-KEY':os.environ.get('WAZEN_ADMIN_KEY','test-admin-key'),
        'X-WAZEN-ADMIN-ACTOR':'ops-qa',
    }


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@app.get('/__qa__/boom-v57')
def _boom_v57():
    raise RuntimeError('synthetic operational test error')


def test_middleware_logs_5xx_without_request_payload_or_headers():
    request_id='ops-500-request'
    secret='must-not-be-persisted'
    r=safe_client.get('/__qa__/boom-v57',headers={
        'X-Request-ID':request_id,
        'X-QA-Secret':secret,
    })
    assert r.status_code==500

    with SessionLocal() as db:
        row=db.scalar(select(OperationalEvent).where(
            OperationalEvent.event_type=='HTTP_5XX',
            OperationalEvent.request_id==request_id,
        ).order_by(OperationalEvent.created_at.desc()))
        assert row is not None
        assert row.path=='/__qa__/boom-v57'
        assert row.method=='GET'
        assert row.status_code==500
        assert secret not in row.details_json


def test_middleware_logs_slow_request_when_threshold_is_exceeded():
    main_module=importlib.import_module('app.main')
    original=main_module.SLOW_REQUEST_MS
    main_module.SLOW_REQUEST_MS=0
    request_id=f"ops-slow-{uuid4().hex[:8]}"
    try:
        r=client.get('/api/v1/health',headers={'X-Request-ID':request_id})
        assert r.status_code==200
    finally:
        main_module.SLOW_REQUEST_MS=original

    with SessionLocal() as db:
        row=db.scalar(select(OperationalEvent).where(
            OperationalEvent.event_type=='SLOW_REQUEST',
            OperationalEvent.request_id==request_id,
        ))
        assert row is not None
        assert row.status_code==200
        assert row.path=='/api/v1/health'


def test_operations_summary_surfaces_operational_and_security_signals():
    now=_now()
    user_id=None
    with SessionLocal() as db:
        log_operational_event(
            db,
            event_type='HTTP_5XX',
            method='GET',
            path='/qa/failure',
            status_code=500,
            duration_ms=50,
            request_id='ops-summary-500',
        )
        rate=AuthRateLimit(
            scope='LOGIN_EMAIL',
            subject_hash=subject_hash(f"ops-{uuid4().hex}@example.com"),
            attempts=5,
            window_started_at=now,
            blocked_until=now+timedelta(minutes=10),
            updated_at=now,
        )
        db.add(rate)
        db.commit()

    r=client.get('/api/v1/admin/operations/summary',headers=_admin_headers())
    assert r.status_code==200, r.text
    data=r.json()['data']
    assert data['metrics']['http_5xx_last_hour']>=1
    assert data['metrics']['active_auth_blocks']>=1
    assert data['status']=='ALERT'
    assert any(x['code']=='HTTP_5XX_PRESENT' for x in data['alerts'])


def test_stale_idempotency_is_reported_as_alert():
    email=f"ops-idem-{uuid4().hex[:8]}@example.com"
    registered=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Ops QA'
    })
    assert registered.status_code==200
    user_id=registered.json()['data']['user_id']
    now=_now()

    with SessionLocal() as db:
        db.add(IdempotencyRecord(
            user_id=user_id,
            method='POST',
            path='/api/v1/food-log',
            idempotency_key=f"stale-{uuid4().hex}",
            request_hash=_payload_hash({'x':1}),
            state='PENDING',
            created_at=now-timedelta(minutes=10),
        ))
        db.commit()

    r=client.get('/api/v1/admin/operations/summary',headers=_admin_headers())
    assert r.status_code==200
    data=r.json()['data']
    assert data['metrics']['stale_idempotency']>=1
    assert any(x['code']=='STALE_IDEMPOTENCY' for x in data['alerts'])


def test_operational_events_admin_api_filters_and_requires_admin_key():
    assert client.get('/api/v1/admin/operational-events').status_code in (401,503)

    with SessionLocal() as db:
        log_operational_event(
            db,event_type='SLOW_REQUEST',method='POST',path='/qa/slow',
            status_code=201,duration_ms=2200,request_id='ops-filter-slow'
        )

    r=client.get('/api/v1/admin/operational-events',headers=_admin_headers(),params={
        'event_type':'SLOW_REQUEST','status_code':201,'limit':10
    })
    assert r.status_code==200
    items=r.json()['data']['items']
    assert items
    assert all(x['event_type']=='SLOW_REQUEST' and x['status_code']==201 for x in items)
