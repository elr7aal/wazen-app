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
    admin_key=os.environ.get('WAZEN_ADMIN_KEY','test-admin-key')
    return {
        'X-WAZEN-ADMIN-KEY':admin_key,
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


def test_password_reset_request_and_completion_are_audited(monkeypatch):
    monkeypatch.setenv('WAZEN_PASSWORD_RESET_DEBUG','1')
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


def test_refresh_success_and_replayed_token_failure_are_audited():
    _, data = _register()
    token = data['refresh_token']
    request_id = f'refresh-{uuid4().hex}'
    success = client.post('/api/v1/auth/refresh', json={'refresh_token': token},
                          headers={'X-Request-ID': request_id})
    assert success.status_code == 200
    failed = client.post('/api/v1/auth/refresh', json={'refresh_token': token},
                         headers={'X-Request-ID': request_id + '-replay'})
    assert failed.status_code == 401
    events = _events(event_type='TOKEN_REFRESH')
    ok = next(x for x in events if x['request_id'] == request_id)
    bad = next(x for x in events if x['request_id'] == request_id + '-replay')
    assert ok['outcome'] == 'SUCCESS'
    assert bad['outcome'] == 'FAILURE'
    assert ok['client_hash'] and bad['client_hash']
    for secret in (token, data['access_token'], success.json()['data']['refresh_token'],
                   success.json()['data']['access_token']):
        assert secret not in str(events)


def test_network_and_email_are_hashed_in_storage_and_admin_response():
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models.db_models import SecurityEvent
    from app.services.auth_rate_limit import subject_hash

    email, _ = _register()
    host = '192.0.2.56'
    request_id = f'network-{uuid4().hex}'
    network_client = TestClient(app, client=(host, 50000))
    response = network_client.post('/api/v1/auth/login',
        json={'email': email, 'password': PASSWORD},
        headers={'X-Request-ID': request_id})
    assert response.status_code == 200
    event = next(x for x in _events(event_type='LOGIN') if x['request_id'] == request_id)
    assert event['client_hash'] == subject_hash(host)
    assert event['subject_hash'] == subject_hash(email)
    assert host not in str(event) and email not in str(event)
    with SessionLocal() as db:
        row = db.scalar(select(SecurityEvent).where(SecurityEvent.request_id == request_id))
        stored = {column.name: getattr(row, column.name) for column in row.__table__.columns}
        assert host not in str(stored) and email not in str(stored)
        assert PASSWORD not in str(stored)


def test_single_session_logout_is_audited():
    _, data = _register()
    request_id = f'logout-{uuid4().hex}'
    response = client.post('/api/v1/auth/logout',
        headers={'Authorization': f"Bearer {data['access_token']}", 'X-Request-ID': request_id},
        json={'refresh_token': data['refresh_token'], 'all_sessions': False})
    assert response.status_code == 200
    event = next(x for x in _events(event_type='LOGOUT') if x['request_id'] == request_id)
    assert event['outcome'] == 'SUCCESS'
    assert event['user_id'] == data['user_id']
    assert event['details']['revoked_sessions'] == 1


def test_password_reset_throttle_is_audited_without_raw_identifiers():
    from app.services.auth_rate_limit import RESET_EMAIL_LIMIT

    email = _email('reset-throttle')
    network_client = TestClient(app, client=('192.0.2.57', 50000))
    prefix = f'reset-block-{uuid4().hex}'
    for attempt in range(RESET_EMAIL_LIMIT + 1):
        response = network_client.post('/api/v1/auth/forgot-password',
            json={'email': email}, headers={'X-Request-ID': f'{prefix}-{attempt}'})
        if response.status_code == 429:
            break
        assert response.status_code == 200
    assert response.status_code == 429
    event = next(x for x in _events(event_type='PASSWORD_RESET_THROTTLED', outcome='BLOCKED')
                 if x['request_id'].startswith(prefix))
    assert event['subject_hash'] and event['client_hash']
    assert email not in str(event) and '192.0.2.57' not in str(event)
    assert event['details']['retry_after'] > 0


def test_request_id_is_bounded_in_response_and_security_event():
    email, _ = _register()
    request_id = uuid4().hex + 'x' * 100
    response = client.post('/api/v1/auth/login',
        json={'email': email, 'password': PASSWORD}, headers={'X-Request-ID': request_id})
    assert response.status_code == 200
    assert response.headers['X-Request-ID'] == request_id[:80]
    assert any(x['request_id'] == request_id[:80] for x in _events(event_type='LOGIN'))


def test_deletion_clears_subject_only_events_and_preserves_other_users():
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models.db_models import SecurityEvent
    from app.services.security_events import log_security_event
    from app.services.auth_rate_limit import subject_hash

    email, data = _register()
    other_email, other = _register()
    with SessionLocal() as db:
        log_security_event(db, event_type='LOGIN', outcome='FAILURE', subject=email)
    response = client.request('DELETE', '/api/v1/users/me',
        headers={'Authorization': f"Bearer {data['access_token']}"},
        json={'password': PASSWORD, 'confirm': 'DELETE'})
    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(SecurityEvent).where(
            (SecurityEvent.user_id == data['user_id']) |
            (SecurityEvent.subject_hash == subject_hash(email)))) is None
        assert db.scalar(select(SecurityEvent).where(
            SecurityEvent.user_id == other['user_id'],
            SecurityEvent.subject_hash == subject_hash(other_email))) is not None


def test_security_retention_removes_expired_events_only():
    from datetime import datetime, timedelta, timezone
    from app.db import SessionLocal
    from app.models.db_models import SecurityEvent
    from app.services.security_events import RETENTION_DAYS, cleanup_security_events

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as db:
        expired = SecurityEvent(event_type='LOGIN', outcome='FAILURE',
            created_at=now - timedelta(days=RETENTION_DAYS, seconds=1))
        current = SecurityEvent(event_type='LOGIN', outcome='SUCCESS', created_at=now)
        db.add_all([expired, current])
        db.commit()
        expired_id, current_id = expired.id, current.id
        assert cleanup_security_events(db, now=now) >= 1
        db.expire_all()
        assert db.get(SecurityEvent, expired_id) is None
        assert db.get(SecurityEvent, current_id) is not None
