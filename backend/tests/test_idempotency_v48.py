from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"idem-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Idem QA'
    })
    assert r.status_code==200
    token=r.json()['data']['access_token']
    return {'Authorization':f'Bearer {token}'}


def test_manual_food_log_replays_same_response_without_duplicate():
    h=_headers()
    payload={
        'food_name':'Idempotent Meal',
        'meal_type':'LUNCH',
        'entry_method':'MANUAL',
        'calories':420,
        'protein_g':31,
        'carbs_g':44,
        'fat_g':13,
        'fiber_g':5,
        'sodium_mg':500,
    }
    headers={**h,'Idempotency-Key':'manual-001'}
    first=client.post('/api/v1/food-log',headers=headers,json=payload)
    second=client.post('/api/v1/food-log',headers=headers,json=payload)
    assert first.status_code==200
    assert second.status_code==200
    assert second.json()==first.json()

    today=client.get('/api/v1/food-log/today',headers=h).json()['data']
    assert len(today['items'])==1
    assert today['totals']['calories']==420


def test_idempotency_key_conflict_on_different_payload():
    h=_headers()
    headers={**h,'Idempotency-Key':'manual-conflict'}
    base={
        'food_name':'Meal A',
        'meal_type':'LUNCH',
        'entry_method':'MANUAL',
        'calories':300,
        'protein_g':20,
        'carbs_g':30,
        'fat_g':10,
        'fiber_g':2,
        'sodium_mg':300,
    }
    first=client.post('/api/v1/food-log',headers=headers,json=base)
    assert first.status_code==200
    changed={**base,'calories':450}
    second=client.post('/api/v1/food-log',headers=headers,json=changed)
    assert second.status_code==409


def test_catalog_log_is_idempotent():
    h=_headers()
    headers={**h,'Idempotency-Key':'catalog-001'}
    payload={
        'food_id':'MCD-AE-001',
        'meal_type':'DINNER',
        'quantity':1,
        'entry_method':'CATALOG',
    }
    first=client.post('/api/v1/food-log/from-catalog',headers=headers,json=payload)
    second=client.post('/api/v1/food-log/from-catalog',headers=headers,json=payload)
    assert first.status_code==200
    assert second.status_code==200
    assert second.json()==first.json()

    today=client.get('/api/v1/food-log/today',headers=h).json()['data']
    assert len(today['items'])==1


def test_no_idempotency_key_keeps_existing_behavior():
    h=_headers()
    payload={
        'food_name':'Normal Retry Meal',
        'meal_type':'SNACK',
        'entry_method':'MANUAL',
        'calories':100,
        'protein_g':5,
        'carbs_g':10,
        'fat_g':4,
        'fiber_g':1,
        'sodium_mg':100,
    }
    assert client.post('/api/v1/food-log',headers=h,json=payload).status_code==200
    assert client.post('/api/v1/food-log',headers=h,json=payload).status_code==200
    today=client.get('/api/v1/food-log/today',headers=h).json()['data']
    assert len(today['items'])==2
