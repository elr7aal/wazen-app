from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"craving-v28-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Craving QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def test_arabic_craving_extracts_explicit_constraints():
    r=client.post('/api/v1/cravings/parse',json={
        'text':'أبي برغر من KFC تحت 650 سعرة ميزانيتي 35 درهم وعلى الأقل 25g بروتين للعشاء'
    })
    assert r.status_code==200
    d=r.json()['data']
    assert d['restaurant']=='KFC UAE'
    assert d['food_category']=='BURGERS'
    assert d['max_calories']==650
    assert d['budget_max']==35
    assert d['min_protein_g']==25
    assert d['meal_type']=='DINNER'
    assert d['preserve_restaurant'] is True
    assert d['explicit']['restaurant'] is True


def test_english_craving_extracts_constraints():
    r=client.post('/api/v1/cravings/parse',json={
        'text':"burger from McDonalds under 700 calories, AED 40, at least 20g protein for dinner"
    })
    assert r.status_code==200
    d=r.json()['data']
    assert d['restaurant']=="McDonald's UAE"
    assert d['food_category']=='BURGERS'
    assert d['max_calories']==700
    assert d['budget_max']==40
    assert d['min_protein_g']==20
    assert d['meal_type']=='DINNER'


def test_calorie_number_is_not_misread_as_budget():
    r=client.post('/api/v1/cravings/parse',json={'text':'برغر تحت 600 سعرة'})
    d=r.json()['data']
    assert d['max_calories']==600
    assert d['budget_max'] is None


def test_golden_flow_preserves_explicit_restaurant_and_min_protein():
    h=_headers()
    client.patch('/api/v1/users/me',headers=h,json={
        'target_calories':2200,
        'target_protein_g':150,
        'daily_budget':100,
    })
    r=client.post('/api/v1/golden-flow',headers=h,json={
        'craving_text':'أبي برغر من KFC تحت 800 سعرة وعلى الأقل 25g بروتين',
        'meal_type':'DINNER',
    })
    assert r.status_code==200,r.text
    d=r.json()['data']
    assert d['parsed_intent']['restaurant']=='KFC UAE'
    assert d['parsed_intent']['preserve_restaurant'] is True
    results=d['recommendations']['results']
    assert results
    assert all(x['vendor']=='KFC UAE' for x in results)
    assert all((x['nutrition']['protein_g'] or 0)>=25 for x in results)
