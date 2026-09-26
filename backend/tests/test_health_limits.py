from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"health-limit-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Health QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def _recommend_mcd_burgers(h):
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':"McDonald's UAE",'category':'BURGERS'
    })
    assert r.status_code==200, r.text
    return r.json()['data']


def test_hard_sodium_limit_excludes_foods_before_ranking():
    h=_headers()
    r=client.put('/api/v1/health-limits',headers=h,json={
        'nutrient_code':'SODIUM_MG',
        'limit_type':'MAX',
        'value':500,
        'unit':'mg',
        'severity':'HARD',
        'source_type':'USER',
        'note':'QA only',
        'active':True,
    })
    assert r.status_code==200

    data=_recommend_mcd_burgers(h)
    assert any(x['food_id']=='MCD-AE-002' and x['reason']=='HEALTH_LIMIT' for x in data['excluded'])
    assert any(x['food_id']=='MCD-AE-001' for x in data['results'])


def test_soft_sodium_limit_warns_without_excluding():
    h=_headers()
    client.put('/api/v1/health-limits',headers=h,json={
        'nutrient_code':'SODIUM_MG','limit_type':'MAX','value':500,'unit':'mg',
        'severity':'SOFT','source_type':'USER','active':True,
    })
    data=_recommend_mcd_burgers(h)
    item=next(x for x in data['results'] if x['food_id']=='MCD-AE-002')
    assert 'SODIUM_MG_MAX_LIMIT' in item['warnings']


def test_missing_required_nutrient_is_not_treated_as_zero_or_safe():
    h=_headers()
    client.put('/api/v1/health-limits',headers=h,json={
        'nutrient_code':'SATURATED_FAT_G','limit_type':'MAX','value':10,'unit':'g',
        'severity':'HARD','source_type':'CLINICIAN','active':True,
    })
    data=_recommend_mcd_burgers(h)
    missing=next(x for x in data['excluded'] if x['food_id']=='MCD-AE-001')
    assert missing['reason']=='HEALTH_LIMIT'
    assert 'MISSING_SATURATED_FAT_G' in missing['details']


def test_health_limits_roundtrip():
    h=_headers()
    client.put('/api/v1/health-limits',headers=h,json={
        'nutrient_code':'SUGAR_G','limit_type':'MAX','value':15,'unit':'g',
        'severity':'SOFT','source_type':'CLINICIAN','note':'Entered from clinician plan','active':True,
    })
    r=client.get('/api/v1/health-limits',headers=h)
    assert r.status_code==200
    item=next(x for x in r.json()['data']['items'] if x['nutrient_code']=='SUGAR_G')
    assert item['source_type']=='CLINICIAN'
    assert item['value']==15
