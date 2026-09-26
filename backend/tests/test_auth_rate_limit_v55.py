from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.db_models import AuthRateLimit
from app.services.auth_rate_limit import LOGIN_EMAIL_LIMIT, RESET_EMAIL_LIMIT, subject_hash

client=TestClient(app)
PASSWORD='StrongPass123!'


def _register():
    email=f"throttle-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':PASSWORD,'first_name':'Throttle QA'
    })
    assert r.status_code==200
    return email


def test_login_blocks_after_repeated_bad_passwords_with_retry_after():
    email=_register()
    last=None
    for i in range(LOGIN_EMAIL_LIMIT):
        last=client.post('/api/v1/auth/login',json={
            'email':email,'password':'WrongPassword999!'
        })
        if i<LOGIN_EMAIL_LIMIT-1:
            assert last.status_code==401
    assert last.status_code==429
    assert int(last.headers['Retry-After'])>=1

    again=client.post('/api/v1/auth/login',json={
        'email':email,'password':PASSWORD
    })
    assert again.status_code==429


def test_successful_login_clears_email_failure_counter():
    email=_register()

    for _ in range(LOGIN_EMAIL_LIMIT-1):
        r=client.post('/api/v1/auth/login',json={
            'email':email,'password':'WrongPassword999!'
        })
        assert r.status_code==401

    good=client.post('/api/v1/auth/login',json={
        'email':email,'password':PASSWORD
    })
    assert good.status_code==200

    # A fresh sequence starts after successful authentication.
    for _ in range(LOGIN_EMAIL_LIMIT-1):
        r=client.post('/api/v1/auth/login',json={
            'email':email,'password':'WrongPassword999!'
        })
        assert r.status_code==401


def test_password_recovery_is_throttled_without_account_enumeration():
    existing=_register()
    missing=f"missing-{uuid4().hex}@example.com"

    for email in [existing,missing]:
        responses=[]
        for _ in range(RESET_EMAIL_LIMIT):
            responses.append(client.post('/api/v1/auth/forgot-password',json={'email':email}))
        assert all(x.status_code==200 for x in responses[:-1])
        assert responses[-1].status_code==429
        assert int(responses[-1].headers['Retry-After'])>=1


def test_rate_limit_storage_never_contains_raw_email():
    email=_register()
    client.post('/api/v1/auth/login',json={
        'email':email,'password':'WrongPassword999!'
    })

    digest=subject_hash(email)
    with SessionLocal() as db:
        row=db.scalar(select(AuthRateLimit).where(
            AuthRateLimit.scope=='LOGIN_EMAIL',
            AuthRateLimit.subject_hash==digest,
        ))
        assert row is not None
        assert row.subject_hash!=email
        assert '@' not in row.subject_hash
        assert len(row.subject_hash)==64
