from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers(prefix='ctx'):
    email=f"{prefix}-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Context QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def test_condition_context_roundtrip():
    h=_headers('ctx-roundtrip')
    r=client.patch('/api/v1/users/me',headers=h,json={
        'condition_context':['DIABETES','KIDNEY']
    })
    assert r.status_code==200
    profile=r.json()['data']['profile']
    assert set(profile['condition_context'])=={'DIABETES','KIDNEY'}

    me=client.get('/api/v1/users/me',headers=h)
    assert me.status_code==200
    assert set(me.json()['data']['profile']['condition_context'])=={'DIABETES','KIDNEY'}


def test_condition_context_alone_does_not_apply_implicit_limits():
    h=_headers('ctx-neutral')
    before=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':"McDonald's UAE",
        'category':'BURGERS',
    })
    assert before.status_code==200
    before_data=before.json()['data']
    before_ids=[x['food_id'] for x in before_data['results']]
    before_excluded=[(x['food_id'],x['reason']) for x in before_data['excluded']]

    update=client.patch('/api/v1/users/me',headers=h,json={
        'condition_context':['DIABETES','HYPERTENSION']
    })
    assert update.status_code==200

    after=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':"McDonald's UAE",
        'category':'BURGERS',
    })
    assert after.status_code==200
    after_data=after.json()['data']
    after_ids=[x['food_id'] for x in after_data['results']]
    after_excluded=[(x['food_id'],x['reason']) for x in after_data['excluded']]

    assert after_ids==before_ids
    assert after_excluded==before_excluded
    assert all(x['reason']!='HEALTH_LIMIT' for x in after_data['excluded'])


def test_onboarding_accepts_optional_condition_context():
    h=_headers('ctx-onboarding')
    r=client.post('/api/v1/onboarding/complete',headers=h,json={
        'first_name':'Context QA',
        'date_of_birth':'1990-01-01',
        'gender':'MALE',
        'height_cm':175,
        'weight_kg':80,
        'target_weight_kg':75,
        'goal_type':'LOSE',
        'activity_level':'LIGHT',
        'daily_budget':50,
        'severe_allergens':[],
        'condition_context':['HYPERTENSION'],
        'food_preferences':[],
        'disliked_foods':[],
    })
    assert r.status_code==200, r.text
    assert r.json()['data']['profile']['condition_context']==['HYPERTENSION']
