from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"prefs-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Prefs QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def _recommend(h):
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'KFC UAE','category':'BURGERS'
    })
    assert r.status_code==200, r.text
    return r.json()['data']


def test_food_never_show_is_hard_user_exclusion():
    h=_headers()
    before=_recommend(h)
    assert any(x['food_id']=='KFC-AE-014' for x in before['results'])

    set_pref=client.put('/api/v1/preferences',headers=h,json={
        'target_type':'FOOD',
        'target_value':'KFC-AE-014',
        'level':'NEVER_SHOW',
    })
    assert set_pref.status_code==200

    after=_recommend(h)
    assert all(x['food_id']!='KFC-AE-014' for x in after['results'])
    assert any(x['food_id']=='KFC-AE-014' and x['reason']=='USER_NEVER_SHOW' for x in after['excluded'])


def test_food_love_increases_preference_score():
    h=_headers()
    before=_recommend(h)
    original=next(x for x in before['results'] if x['food_id']=='KFC-AE-014')

    r=client.put('/api/v1/preferences',headers=h,json={
        'target_type':'FOOD',
        'target_value':'KFC-AE-014',
        'level':'LOVE',
    })
    assert r.status_code==200

    after=_recommend(h)
    loved=next(x for x in after['results'] if x['food_id']=='KFC-AE-014')
    assert loved['scores']['preference'] > original['scores']['preference']
    assert any('LOVE' in x for x in loved['reasons'])


def test_term_never_show_matches_alias_text():
    h=_headers()
    r=client.put('/api/v1/preferences',headers=h,json={
        'target_type':'TERM',
        'target_value':'ZINGER',
        'level':'NEVER_SHOW',
    })
    assert r.status_code==200
    after=_recommend(h)
    assert all('ZINGER' not in (x['name'] or '').upper() for x in after['results'])


def test_preferences_list_roundtrip():
    h=_headers()
    client.put('/api/v1/preferences',headers=h,json={
        'target_type':'TERM','target_value':'CHICKEN','level':'LIKE'
    })
    r=client.get('/api/v1/preferences',headers=h)
    assert r.status_code==200
    items=r.json()['data']['items']
    assert any(x['target_type']=='TERM' and x['target_value']=='CHICKEN' and x['level']=='LIKE' for x in items)
