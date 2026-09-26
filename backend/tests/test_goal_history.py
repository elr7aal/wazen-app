from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _register():
    email=f"goal-history-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Goal QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def _onboard(h):
    r=client.post('/api/v1/onboarding/complete',headers=h,json={
        'first_name':'Goal QA',
        'date_of_birth':'1990-01-01',
        'gender':'MALE',
        'height_cm':175,
        'weight_kg':82,
        'target_weight_kg':76,
        'goal_type':'LOSE',
        'activity_level':'LIGHT',
        'daily_budget':45,
        'severe_allergens':[],
        'food_preferences':['CHICKEN'],
        'disliked_foods':[],
    })
    assert r.status_code==200


def test_onboarding_creates_goal_history():
    h=_register()
    _onboard(h)
    r=client.get('/api/v1/profile/history',headers=h)
    assert r.status_code==200
    data=r.json()['data']
    assert data['count']>=1
    first=data['items'][0]
    assert first['reason']=='ONBOARDING'
    assert first['snapshot']['goal_type']=='LOSE'
    assert first['snapshot']['target_weight_kg']==76


def test_goal_change_adds_history_but_duplicate_snapshot_is_skipped():
    h=_register()
    _onboard(h)
    before=client.get('/api/v1/profile/history',headers=h).json()['data']['count']

    changed=client.patch('/api/v1/users/me',headers=h,json={
        'goal_type':'MAINTAIN',
        'target_weight_kg':78,
    })
    assert changed.status_code==200
    after_change=client.get('/api/v1/profile/history',headers=h).json()['data']
    assert after_change['count']==before+1
    assert after_change['items'][0]['snapshot']['goal_type']=='MAINTAIN'

    same=client.patch('/api/v1/users/me',headers=h,json={
        'goal_type':'MAINTAIN',
        'target_weight_kg':78,
    })
    assert same.status_code==200
    after_same=client.get('/api/v1/profile/history',headers=h).json()['data']['count']
    assert after_same==after_change['count']
