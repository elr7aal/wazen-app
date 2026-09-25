from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"rank-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Rank QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def test_rank_scores_are_bounded_reasons_are_present_and_vendor_is_preserved():
    h=_headers()
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'KFC UAE',
        'category':'BURGERS',
        'max_calories':700,
        'budget_max':50,
        'allow_modifications':True,
    })
    assert r.status_code==200, r.text
    data=r.json()['data']
    assert data['results']
    assert data['decision_audit_count']==len(data['results'])

    for item in data['results']:
        assert item['vendor']=='KFC UAE'
        assert item['reasons']
        for value in item['scores'].values():
            assert 0 <= value <= 100


def test_rank_order_is_decision_priority_then_wazen_score():
    h=_headers()
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':"McDonald's UAE",
        'category':'BURGERS',
        'max_calories':500,
        'budget_max':50,
    })
    assert r.status_code==200
    items=r.json()['data']['results']
    priority={'ELIGIBLE':0,'NEAR_MATCH':1,'MAKE_IT_FIT':2,'OVER_TARGET':3}
    keys=[(priority[x['decision']],-x['scores']['wazen']) for x in items]
    assert keys==sorted(keys)


def test_decision_audit_keeps_scores_reasons_and_context():
    h=_headers()
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'KFC UAE',
        'category':'BURGERS',
        'max_calories':650,
        'budget_max':40,
    })
    assert r.status_code==200
    first=r.json()['data']['results'][0]

    audit=client.get('/api/v1/recommendations/decisions',headers=h,params={
        'food_id':first['food_id'],
        'limit':10,
    })
    assert audit.status_code==200
    data=audit.json()['data']
    assert data['engine_version']=='v1'
    assert data['items']
    row=data['items'][0]
    assert row['food_id']==first['food_id']
    assert row['scores']['wazen']==first['scores']['wazen']
    assert row['reasons']==first['reasons']
    assert row['context']['vendor']=='KFC UAE'
    assert row['context']['max_calories']==650
    assert row['context']['budget_max']==40
    assert row['engine_version']=='v1'
