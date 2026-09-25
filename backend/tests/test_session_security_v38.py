from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def test_active_sessions_and_logout_all_revokes_every_refresh_token():
    email=f"session-all-{uuid4().hex[:8]}@example.com"
    register=client.post('/api/v1/auth/register',json={
        'email':email,
        'password':'StrongPass123!',
        'first_name':'Session QA',
    })
    assert register.status_code==200
    first=register.json()['data']

    login=client.post('/api/v1/auth/login',json={
        'email':email,
        'password':'StrongPass123!',
    })
    assert login.status_code==200
    second=login.json()['data']

    headers={'Authorization':f"Bearer {second['access_token']}"}
    sessions=client.get('/api/v1/auth/sessions',headers=headers)
    assert sessions.status_code==200
    assert sessions.json()['data']['count']>=2

    logout=client.post('/api/v1/auth/logout',headers=headers,json={
        'refresh_token':second['refresh_token'],
        'all_sessions':True,
    })
    assert logout.status_code==200
    assert logout.json()['data']['revoked_sessions']>=2

    sessions_after=client.get('/api/v1/auth/sessions',headers=headers)
    assert sessions_after.status_code==200
    assert sessions_after.json()['data']['count']==0

    first_refresh=client.post('/api/v1/auth/refresh',json={'refresh_token':first['refresh_token']})
    second_refresh=client.post('/api/v1/auth/refresh',json={'refresh_token':second['refresh_token']})
    assert first_refresh.status_code==401
    assert second_refresh.status_code==401
