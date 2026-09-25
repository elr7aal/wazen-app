from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"retry-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Retry QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def test_golden_flow_auto_log_is_idempotent():
    h=_headers()
    headers={**h,'Idempotency-Key':'golden-auto-001'}
    payload={
        'craving_text':'burger',
        'meal_type':'DINNER',
        'quantity':1,
        'allow_modifications':True,
        'auto_log_food_id':'MCD-AE-001',
    }
    first=client.post('/api/v1/golden-flow',headers=headers,json=payload)
    second=client.post('/api/v1/golden-flow',headers=headers,json=payload)
    assert first.status_code==200, first.text
    assert second.status_code==200, second.text
    assert second.json()==first.json()

    today=client.get('/api/v1/food-log/today',headers=h).json()['data']
    assert len(today['items'])==1
    assert today['items'][0]['food_id']=='MCD-AE-001'


def test_golden_flow_conflicts_when_same_key_payload_changes():
    h=_headers()
    headers={**h,'Idempotency-Key':'golden-conflict-001'}
    base={
        'craving_text':'burger',
        'meal_type':'DINNER',
        'quantity':1,
        'allow_modifications':True,
        'auto_log_food_id':'MCD-AE-001',
    }
    assert client.post('/api/v1/golden-flow',headers=headers,json=base).status_code==200
    changed={**base,'quantity':2}
    assert client.post('/api/v1/golden-flow',headers=headers,json=changed).status_code==409


def test_activity_log_is_idempotent():
    h=_headers()
    headers={**h,'Idempotency-Key':'activity-001'}
    payload={
        'calories_credit':250,
        'source':'MANUAL',
        'note':'QA walk',
    }
    first=client.post('/api/v1/activity-log',headers=headers,json=payload)
    second=client.post('/api/v1/activity-log',headers=headers,json=payload)
    assert first.status_code==200
    assert second.status_code==200
    assert second.json()==first.json()

    today=client.get('/api/v1/activity-log/today',headers=h).json()['data']
    assert today['activity_credit']==250
    assert len(today['items'])==1


def test_activity_log_conflict_on_changed_payload():
    h=_headers()
    headers={**h,'Idempotency-Key':'activity-conflict-001'}
    assert client.post('/api/v1/activity-log',headers=headers,json={
        'calories_credit':100,'source':'MANUAL','note':'first'
    }).status_code==200
    assert client.post('/api/v1/activity-log',headers=headers,json={
        'calories_credit':200,'source':'MANUAL','note':'changed'
    }).status_code==409
