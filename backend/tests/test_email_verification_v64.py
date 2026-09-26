from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.main import app
from app.models.db_models import EmailVerificationToken, User
from app.services.auth_sessions import utcnow
from app.services.email_verification import create_email_verification

client=TestClient(app)
PASSWORD='StrongPass123!'


def _register():
    email=f"verify-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,
        'password':PASSWORD,
        'first_name':'Verify QA',
    })
    assert r.status_code==200, r.text
    data=r.json()['data']
    return email,data,{'Authorization':f"Bearer {data['access_token']}"}


def _new_raw_token(email):
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email==email))
        assert user is not None
        return create_email_verification(db,user,replace_pending=True)


def test_new_account_starts_unverified_and_me_exposes_state():
    email,data,h=_register()
    assert data['email_verified'] is False
    assert data['verification_delivery'] in {'NOT_CONFIGURED','SENT','FAILED'}

    me=client.get('/api/v1/users/me',headers=h)
    assert me.status_code==200
    payload=me.json()['data']
    assert payload['email']==email
    assert payload['email_verified'] is False
    assert payload['email_verified_at'] is None


def test_verification_token_is_single_use_and_updates_account():
    email,_,h=_register()
    raw=_new_raw_token(email)

    first=client.post('/api/v1/auth/verify-email',json={'token':raw})
    assert first.status_code==200, first.text
    assert first.json()['data']['verified'] is True

    me=client.get('/api/v1/users/me',headers=h)
    assert me.status_code==200
    assert me.json()['data']['email_verified'] is True
    assert me.json()['data']['email_verified_at']

    reused=client.post('/api/v1/auth/verify-email',json={'token':raw})
    assert reused.status_code==400


def test_resend_is_rate_limited_then_allowed_after_cooldown():
    email,_,h=_register()

    immediate=client.post('/api/v1/auth/resend-verification',headers=h)
    assert immediate.status_code==429
    assert int(immediate.headers['Retry-After'])>=1

    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email==email))
        rows=db.scalars(select(EmailVerificationToken).where(
            EmailVerificationToken.user_id==user.id,
            EmailVerificationToken.used_at.is_(None),
        )).all()
        assert rows
        for row in rows:
            row.created_at=utcnow()-timedelta(minutes=5)
        db.commit()

    resend=client.post('/api/v1/auth/resend-verification',headers=h)
    assert resend.status_code==200, resend.text
    data=resend.json()['data']
    assert data['accepted'] is True
    assert data['already_verified'] is False
    assert data['delivery'] in {'NOT_CONFIGURED','SENT','FAILED'}


def test_resend_after_verification_is_noop():
    email,_,h=_register()
    raw=_new_raw_token(email)
    assert client.post('/api/v1/auth/verify-email',json={'token':raw}).status_code==200

    resend=client.post('/api/v1/auth/resend-verification',headers=h)
    assert resend.status_code==200
    assert resend.json()['data']=={
        'accepted':True,
        'already_verified':True,
        'delivery':'NOT_NEEDED',
    }


def test_account_deletion_purges_verification_tokens():
    email,data,h=_register()
    user_id=data['user_id']

    with SessionLocal() as db:
        count=db.scalar(select(func.count()).select_from(EmailVerificationToken).where(
            EmailVerificationToken.user_id==user_id
        ))
        assert count and count>0

    deleted=client.request('DELETE','/api/v1/users/me',headers=h,json={
        'password':PASSWORD,
        'confirm':'DELETE',
    })
    assert deleted.status_code==200, deleted.text

    with SessionLocal() as db:
        count=db.scalar(select(func.count()).select_from(EmailVerificationToken).where(
            EmailVerificationToken.user_id==user_id
        ))
        assert count==0
