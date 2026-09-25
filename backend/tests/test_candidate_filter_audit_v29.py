from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"audit-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Audit QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def test_severe_allergy_exclusion_is_audited_before_ranking():
    h=_headers()
    p=client.patch('/api/v1/users/me',headers=h,json={'severe_allergens':['GLUTEN']})
    assert p.status_code==200

    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'KFC UAE',
        'category':'BURGERS',
        'budget_max':50,
    })
    assert r.status_code==200, r.text
    data=r.json()['data']
    assert all(x['food_id']!='KFC-AE-014' for x in data['results'])
    assert any(x['food_id']=='KFC-AE-014' and x['reason']=='SEVERE_ALLERGY' for x in data['excluded'])
    assert data['exclusion_audit_count']>=1

    audit=client.get('/api/v1/recommendations/exclusions',headers=h,params={'reason':'SEVERE_ALLERGY'})
    assert audit.status_code==200
    items=audit.json()['data']['items']
    row=next(x for x in items if x['food_id']=='KFC-AE-014')
    assert row['reason']=='SEVERE_ALLERGY'
    assert row['context']['vendor']=='KFC UAE'
    assert row['context']['budget_max']==50
    assert row['context']['min_protein_g'] is None


def test_never_show_exclusion_is_audited():
    h=_headers()
    pref=client.put('/api/v1/preferences',headers=h,json={
        'target_type':'FOOD',
        'target_value':'KFC-AE-014',
        'level':'NEVER_SHOW',
    })
    assert pref.status_code==200

    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'KFC UAE','category':'BURGERS'
    })
    assert r.status_code==200
    assert any(x['food_id']=='KFC-AE-014' and x['reason']=='USER_NEVER_SHOW' for x in r.json()['data']['excluded'])

    audit=client.get('/api/v1/recommendations/exclusions',headers=h,params={'reason':'USER_NEVER_SHOW'})
    assert audit.status_code==200
    assert any(x['food_id']=='KFC-AE-014' for x in audit.json()['data']['items'])


def test_health_hard_limit_exclusion_is_audited_with_details():
    h=_headers()
    limit=client.put('/api/v1/health-limits',headers=h,json={
        'nutrient_code':'SODIUM_MG',
        'limit_type':'MAX',
        'value':500,
        'unit':'mg',
        'severity':'HARD',
        'source_type':'USER',
        'active':True,
    })
    assert limit.status_code==200

    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':"McDonald's UAE",'category':'BURGERS'
    })
    assert r.status_code==200
    audit=client.get('/api/v1/recommendations/exclusions',headers=h,params={'reason':'HEALTH_LIMIT'})
    assert audit.status_code==200
    items=audit.json()['data']['items']
    row=next(x for x in items if x['food_id']=='MCD-AE-002')
    assert 'SODIUM_MG_MAX_LIMIT' in row['details']
