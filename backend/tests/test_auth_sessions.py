import os
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def register_user():
    email=f"session-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,
        'password':'StrongPass123!',
        'first_name':'Session QA',
    })
    assert r.status_code==200, r.text
    return email,r.json()['data']


def test_register_returns_refresh_token_and_rotation_is_one_time():
    email,data=register_user()
    assert data['access_token']
    assert data['refresh_token']
    old=data['refresh_token']

    r=client.post('/api/v1/auth/refresh',json={'refresh_token':old})
    assert r.status_code==200, r.text
    rotated=r.json()['data']
    assert rotated['access_token']
    assert rotated['refresh_token'] != old

    reused=client.post('/api/v1/auth/refresh',json={'refresh_token':old})
    assert reused.status_code==401

    valid=client.post('/api/v1/auth/refresh',json={'refresh_token':rotated['refresh_token']})
    assert valid.status_code==200


def test_logout_revokes_current_refresh_session():
    _,data=register_user()
    headers={'Authorization':f"Bearer {data['access_token']}"}
    r=client.post('/api/v1/auth/logout',headers=headers,json={
        'refresh_token':data['refresh_token'],
        'all_sessions':False,
    })
    assert r.status_code==200
    assert r.json()['data']['logged_out'] is True

    refresh=client.post('/api/v1/auth/refresh',json={'refresh_token':data['refresh_token']})
    assert refresh.status_code==401


def test_password_reset_is_generic_and_revokes_old_sessions():
    email,data=register_user()
    os.environ['WAZEN_PASSWORD_RESET_DEBUG']='1'

    forgot=client.post('/api/v1/auth/forgot-password',json={'email':email})
    assert forgot.status_code==200
    reset_token=forgot.json()['data'].get('debug_reset_token')
    assert reset_token

    reset=client.post('/api/v1/auth/reset-password',json={
        'token':reset_token,
        'new_password':'NewStrongPass456!',
    })
    assert reset.status_code==200

    old_refresh=client.post('/api/v1/auth/refresh',json={'refresh_token':data['refresh_token']})
    assert old_refresh.status_code==401

    old_login=client.post('/api/v1/auth/login',json={'email':email,'password':'StrongPass123!'})
    assert old_login.status_code==401

    new_login=client.post('/api/v1/auth/login',json={'email':email,'password':'NewStrongPass456!'})
    assert new_login.status_code==200


def test_forgot_password_does_not_reveal_missing_account():
    os.environ['WAZEN_PASSWORD_RESET_DEBUG']='1'
    r=client.post('/api/v1/auth/forgot-password',json={'email':f"missing-{uuid4().hex}@example.com"})
    assert r.status_code==200
    data=r.json()['data']
    assert data['accepted'] is True
    assert 'debug_reset_token' not in data
