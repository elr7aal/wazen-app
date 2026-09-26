from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"mutation-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Mutation QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def _add_log(h):
    r=client.post('/api/v1/food-log',headers=h,json={
        'food_name':'Mutation Meal',
        'meal_type':'LUNCH',
        'entry_method':'MANUAL',
        'calories':320,
        'protein_g':24,
        'carbs_g':30,
        'fat_g':10,
        'fiber_g':4,
        'sodium_mg':350,
    })
    assert r.status_code==200
    return r.json()['data']['log_id']


def test_feedback_retry_is_idempotent():
    h=_headers()
    headers={**h,'Idempotency-Key':'feedback-001'}
    payload={'food_id':'MCD-AE-001','action':'SAVE'}
    first=client.post('/api/v1/recommendations/feedback',headers=headers,json=payload)
    second=client.post('/api/v1/recommendations/feedback',headers=headers,json=payload)
    assert first.status_code==200
    assert second.status_code==200
    assert second.json()==first.json()


def test_favorite_retry_replays_original_created_response():
    h=_headers()
    log_id=_add_log(h)
    headers={**h,'Idempotency-Key':'favorite-save-001'}
    first=client.post(f'/api/v1/food-log/{log_id}/favorite',headers=headers)
    second=client.post(f'/api/v1/food-log/{log_id}/favorite',headers=headers)
    assert first.status_code==200
    assert first.json()['data']['created'] is True
    assert second.json()==first.json()


def test_week_generation_retry_replays_same_ids():
    h=_headers()
    headers={**h,'Idempotency-Key':'week-generate-001'}
    first=client.post('/api/v1/plan/week/generate',headers=headers)
    second=client.post('/api/v1/plan/week/generate',headers=headers)
    assert first.status_code==200, first.text
    assert second.status_code==200
    assert second.json()==first.json()


def test_day_rebalance_retry_replays_same_plan():
    h=_headers()
    week=client.get('/api/v1/plan/week',headers=h)
    assert week.status_code==200
    d=week.json()['data']['days'][0]['date']
    headers={**h,'Idempotency-Key':'day-rebalance-001'}
    first=client.post(f'/api/v1/plan/day/{d}/rebalance',headers=headers)
    second=client.post(f'/api/v1/plan/day/{d}/rebalance',headers=headers)
    assert first.status_code==200, first.text
    assert second.status_code==200
    assert second.json()==first.json()
