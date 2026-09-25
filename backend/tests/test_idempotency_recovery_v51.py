from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.db_models import IdempotencyRecord, User
from app.services.idempotency import (
    RETENTION_HOURS,
    STALE_SECONDS,
    _payload_hash,
    begin_idempotent,
    finish_idempotent,
)

client=TestClient(app)


def _user_id():
    email=f"idem-recovery-{datetime.now(timezone.utc).replace(tzinfo=None).timestamp()}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,
        'password':'StrongPass123!',
        'first_name':'Recovery QA',
    })
    assert r.status_code==200
    with SessionLocal() as db:
        return db.scalar(select(User.id).where(User.email==email))


def test_stale_pending_claim_can_be_recovered_and_completed():
    user_id=_user_id()
    payload={'food_name':'Recovered Meal','calories':400}
    key='stale-pending-001'
    path='/api/v1/food-log'

    with SessionLocal() as db:
        row=IdempotencyRecord(
            user_id=user_id,
            method='POST',
            path=path,
            idempotency_key=key,
            request_hash=_payload_hash(payload),
            state='PENDING',
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(seconds=STALE_SECONDS+10),
        )
        db.add(row)
        db.commit()

    with SessionLocal() as db:
        claim=begin_idempotent(
            db,user_id=user_id,method='POST',path=path,key=key,payload=payload
        )
        assert claim['mode']=='CLAIM'
        assert claim.get('recovered') is True
        finish_idempotent(db,claim['record'],{'success':True,'data':{'log_id':'same'}})

    with SessionLocal() as db:
        replay=begin_idempotent(
            db,user_id=user_id,method='POST',path=path,key=key,payload=payload
        )
        assert replay['mode']=='REPLAY'
        assert replay['response']['data']['log_id']=='same'


def test_non_stale_pending_claim_still_blocks_parallel_retry():
    user_id=_user_id()
    payload={'x':1}
    key='fresh-pending-001'
    path='/api/v1/activity-log'

    with SessionLocal() as db:
        row=IdempotencyRecord(
            user_id=user_id,
            method='POST',
            path=path,
            idempotency_key=key,
            request_hash=_payload_hash(payload),
            state='PENDING',
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(row)
        db.commit()

    with SessionLocal() as db:
        try:
            begin_idempotent(
                db,user_id=user_id,method='POST',path=path,key=key,payload=payload
            )
            assert False,'fresh PENDING key should be blocked'
        except ValueError as exc:
            assert str(exc)=='IDEMPOTENCY_IN_PROGRESS'


def test_old_completed_records_are_cleaned_on_next_protected_write():
    user_id=_user_id()
    old_id=None
    with SessionLocal() as db:
        old=IdempotencyRecord(
            user_id=user_id,
            method='POST',
            path='/old',
            idempotency_key='old-completed-001',
            request_hash=_payload_hash({'old':True}),
            state='COMPLETED',
            response_json='{"success":true}',
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(hours=RETENTION_HOURS+2),
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(hours=RETENTION_HOURS+1),
        )
        db.add(old)
        db.commit()
        old_id=old.id

    with SessionLocal() as db:
        claim=begin_idempotent(
            db,
            user_id=user_id,
            method='POST',
            path='/api/v1/activity-log',
            key='new-cleanup-trigger',
            payload={'calories_credit':100},
        )
        assert claim['mode']=='CLAIM'
        assert db.get(IdempotencyRecord,old_id) is None



def test_stale_key_with_different_payload_still_conflicts():
    user_id=_user_id()
    key='stale-conflict-001'
    path='/api/v1/food-log'
    original={'food_name':'Original','calories':300}

    with SessionLocal() as db:
        row=IdempotencyRecord(
            user_id=user_id,
            method='POST',
            path=path,
            idempotency_key=key,
            request_hash=_payload_hash(original),
            state='PENDING',
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(seconds=STALE_SECONDS+10),
        )
        db.add(row)
        db.commit()

    with SessionLocal() as db:
        try:
            begin_idempotent(
                db,
                user_id=user_id,
                method='POST',
                path=path,
                key=key,
                payload={'food_name':'Changed','calories':450},
            )
            assert False,'stale key must not be reusable for a different payload'
        except ValueError as exc:
            assert str(exc)=='IDEMPOTENCY_PAYLOAD_CONFLICT'


def test_retention_does_not_delete_recent_completed_record():
    user_id=_user_id()
    key='recent-completed-001'
    path='/api/v1/activity-log'
    payload={'calories_credit':80}

    with SessionLocal() as db:
        row=IdempotencyRecord(
            user_id=user_id,
            method='POST',
            path=path,
            idempotency_key=key,
            request_hash=_payload_hash(payload),
            state='COMPLETED',
            response_json='{"success":true,"data":{"activity_credit":80}}',
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(minutes=10),
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(minutes=9),
        )
        db.add(row)
        db.commit()

    with SessionLocal() as db:
        replay=begin_idempotent(
            db,
            user_id=user_id,
            method='POST',
            path=path,
            key=key,
            payload=payload,
        )
        assert replay['mode']=='REPLAY'
        assert replay['response']['data']['activity_credit']==80
