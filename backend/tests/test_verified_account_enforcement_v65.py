import os
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.db_models import User

client=TestClient(app)


def _register():
    email=f"verify-gate-{uuid4().hex[:8]}@example.com"
    password='StrongPass123!'
    r=client.post('/api/v1/auth/register',json={
        'email':email,
        'password':password,
        'first_name':'Verify Gate QA',
    })
    assert r.status_code==200, r.text
    data=r.json()['data']
    return email,password,data,{'Authorization':f"Bearer {data['access_token']}"}


def _set_verified(email: str, value: bool):
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email==email))
        assert user
        user.email_verified=value
        db.commit()


def test_unverified_account_is_blocked_from_core_when_enforced(monkeypatch):
    monkeypatch.setenv('WAZEN_REQUIRE_EMAIL_VERIFIED','true')
    email,_,_,h=_register()

    me=client.get('/api/v1/users/me',headers=h)
    assert me.status_code==200
    assert me.json()['data']['email_verified'] is False

    blocked=client.get('/api/v1/nutrition/today',headers=h)
    assert blocked.status_code==403
    assert blocked.json()['detail']=='EMAIL_VERIFICATION_REQUIRED'

    sessions=client.get('/api/v1/auth/sessions',headers=h)
    assert sessions.status_code==200

    export=client.get('/api/v1/users/me/export',headers=h)
    assert export.status_code==200

    _set_verified(email,True)
    allowed=client.get('/api/v1/nutrition/today',headers=h)
    assert allowed.status_code==200


def test_development_can_explicitly_disable_verification_gate(monkeypatch):
    monkeypatch.setenv('WAZEN_ENV','development')
    monkeypatch.setenv('WAZEN_REQUIRE_EMAIL_VERIFIED','false')
    _,_,_,h=_register()
    r=client.get('/api/v1/nutrition/today',headers=h)
    assert r.status_code==200


def test_production_defaults_to_verification_enforcement(monkeypatch):
    monkeypatch.setenv('WAZEN_ENV','production')
    monkeypatch.delenv('WAZEN_REQUIRE_EMAIL_VERIFIED',raising=False)
    _,_,_,h=_register()
    r=client.get('/api/v1/nutrition/today',headers=h)
    assert r.status_code==403
    assert r.json()['detail']=='EMAIL_VERIFICATION_REQUIRED'


def test_capabilities_expose_verification_enforcement(monkeypatch):
    monkeypatch.setenv('WAZEN_REQUIRE_EMAIL_VERIFIED','true')
    r=client.get('/api/v1/capabilities')
    assert r.status_code==200
    assert r.json()['data']['email_verification']['enforced'] is True

    monkeypatch.setenv('WAZEN_REQUIRE_EMAIL_VERIFIED','false')
    r=client.get('/api/v1/capabilities')
    assert r.status_code==200
    assert r.json()['data']['email_verification']['enforced'] is False


def test_unverified_user_can_logout_when_enforced(monkeypatch):
    monkeypatch.setenv('WAZEN_REQUIRE_EMAIL_VERIFIED','true')
    _,_,data,h=_register()
    r=client.post('/api/v1/auth/logout',headers=h,json={
        'refresh_token':data['refresh_token'],
        'all_sessions':False,
    })
    assert r.status_code==200
    assert r.json()['data']['logged_out'] is True
