from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def test_direct_recommendation_contract_accepts_min_protein():
    email=f"contract-{uuid4().hex[:8]}@example.com"
    reg=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Contract QA'
    })
    assert reg.status_code==200
    h={'Authorization':f"Bearer {reg.json()['data']['access_token']}"}

    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'KFC UAE',
        'category':'BURGERS',
        'max_calories':800,
        'min_protein_g':30,
        'budget_max':100,
    })
    assert r.status_code==200,r.text
    data=r.json()['data']
    assert data['results']
    assert all((x['nutrition']['protein_g'] or 0)>=30 for x in data['results'])
    assert all(x['vendor']=='KFC UAE' for x in data['results'])

    audit=client.get('/api/v1/recommendations/decisions',headers=h,params={'limit':20})
    assert audit.status_code==200
    assert any(x['context']['min_protein_g']==30 for x in audit.json()['data']['items'])
