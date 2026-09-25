import os
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client=TestClient(app)
PASSWORD='StrongPass123!'


def _email(prefix='security'):
    return f"{prefix}-{uuid4().hex[:10]}@example.com"


def _register(email=None):
    email=email or _email()
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':PASSWORD,'first_name':'Security QA'
    })
    assert r.status_code==200, r.text
    return email,r.json()['data']


def _admin_headers():
    os.environ['WAZEN_ADMIN_KEY']='security-admin-key'
    return {
        'X-WAZEN-ADMIN-KEY':'security-admin-key',
        'X-WAZEN-ADMIN-ACTOR':'security-qa',
    }


def _events(**params):
    r=client.get('/api/v1/admin/security-events',headers=_admin_headers(),params=params)
    assert r.status_code==200, r.text
    return r.json()['data']['items']


def test_login_success_and_failure_are_audited_without_raw_email():
    email,_=_register()

    failed=client.post('/api/v1/auth/login',json={'email':email,'password':'WrongPass123!'},headers={'X-Request-ID':'req-login-fail'})
    assert failed.status_code==401

    success=client.post('/api/v1/auth/login',json={'email':email,'password':PASSWORD},headers={'X-Request-ID':'req-login-ok'})
    assert success.status_code==200

    events=_events(event_type='LOGIN',limit=50)
    fail=next(x for x in events if x['request_id']=='req-login-fail')
    ok=next(x for x in events if x['request_id']=='req-login-ok')
    assert fail['outcome']=='FAILURE'
    assert ok['outcome']=='SUCCESS'
    assert fail['subject_hash']
    assert ok['subject_hash']
    assert fail['subject_hash']==ok['subject_hash']

    raw=str(events)
    assert email not in raw
    assert 'WrongPass123!' not in raw
    assert PASSWORD not in raw


def test_logout_all_is_audited_with_revoked_count():
    email,data=_register()
    # Add another active session.
    login=client.post('/api/v1/auth/login',json={'email':email,'password':PASSWORD})
    assert login.status_code==200

    r=client.post('/api/v1/auth/logout',headers={
        'Authorization':f"Bearer {data['access_token']}",
        'X-Request-ID':'req-logout-all',
    },json={
        'refresh_token':data['refresh_token'],
        'all_sessions':True,
    })
    assert r.status_code==200

    events=_events(event_type='LOGOUT_ALL',outcome='SUCCESS')
    event=next(x for x in events if x['request_id']=='req-logout-all')
    assert event['user_id']==data['user_id']
    assert event['details']['revoked_sessions']>=2


def test_password_reset_request_and_completion_are_audited():
    os.environ['WAZEN_PASSWORD_RESET_DEBUG']='1'
    email,_=_register()

    requested=client.post('/api/v1/auth/forgot-password',headers={'X-Request-ID':'req-reset-request'},json={'email':email})
    assert requested.status_code==200, requested.text
    token=requested.json()['data']['debug_reset_token']

    reset=client.post('/api/v1/auth/reset-password',headers={'X-Request-ID':'req-reset-success'},json={
        'token':token,
        'new_password':'NewStrongPass456!',
    })
    assert reset.status_code==200, reset.text

    request_events=_events(event_type='PASSWORD_RESET_REQUEST')
    req_event=next(x for x in request_events if x['request_id']=='req-reset-request')
    assert req_event['outcome']=='ACCEPTED'
    assert req_event['subject_hash']

    reset_events=_events(event_type='PASSWORD_RESET')
    done=next(x for x in reset_events if x['request_id']=='req-reset-success')
    assert done['outcome']=='SUCCESS'
    assert done['user_id']


def test_invalid_reset_token_is_audited_without_token_material():
    fake='x'*48
    r=client.post('/api/v1/auth/reset-password',headers={'X-Request-ID':'req-reset-fail'},json={
        'token':fake,
        'new_password':'NewStrongPass456!',
    })
    assert r.status_code==400

    events=_events(event_type='PASSWORD_RESET',outcome='FAILURE')
    event=next(x for x in events if x['request_id']=='req-reset-fail')
    assert fake not in str(event)
    assert event['subject_hash'] is None


def test_login_throttle_is_audited():
    email,_=_register()
    blocked=None
    for i in range(8):
        r=client.post('/api/v1/auth/login',headers={'X-Request-ID':f'req-throttle-{i}'},json={
            'email':email,
            'password':'WrongPass123!',
        })
        if r.status_code==429:
            blocked=r
            break
    assert blocked is not None

    events=_events(event_type='LOGIN_THROTTLED',outcome='BLOCKED',limit=50)
    assert any(x['request_id'] and x['request_id'].startswith('req-throttle-') for x in events)


def test_admin_security_events_requires_admin_key_and_supports_filters():
    assert client.get('/api/v1/admin/security-events').status_code in (401,503)
    r=client.get('/api/v1/admin/security-events',headers=_admin_headers(),params={
        'event_type':'LOGIN','outcome':'SUCCESS','limit':5
    })
    assert r.status_code==200
    items=r.json()['data']['items']
    assert len(items)<=5
    assert all(x['event_type']=='LOGIN' and x['outcome']=='SUCCESS' for x in items)


def test_account_deletion_removes_user_linked_and_subject_events():
    email,data=_register()
    login=client.post('/api/v1/auth/login',headers={'X-Request-ID':'req-before-delete'},json={
        'email':email,'password':PASSWORD
    })
    assert login.status_code==200

    before=_events(event_type='LOGIN')
    assert any(x['request_id']=='req-before-delete' for x in before)

    deleted=client.request('DELETE','/api/v1/users/me',headers={
        'Authorization':f"Bearer {data['access_token']}",
    },json={'password':PASSWORD,'confirm':'DELETE'})
    assert deleted.status_code==200, deleted.text

    after=_events(event_type='LOGIN')
    assert all(x['request_id']!='req-before-delete' for x in after)
