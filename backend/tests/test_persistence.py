from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def auth_headers(email='alpha@example.com'):
    r = client.post('/api/v1/auth/register', json={'email':email,'password':'StrongPass123','first_name':'Alpha'})
    if r.status_code == 409:
        r = client.post('/api/v1/auth/login', json={'email':email,'password':'StrongPass123'})
    assert r.status_code == 200, r.text
    token = r.json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_register_profile_foodlog_and_personal_recommendation():
    h = auth_headers('persist-flow@example.com')
    r = client.patch('/api/v1/users/me', headers=h, json={
        'target_calories': 2000,
        'target_protein_g': 140,
        'target_carbs_g': 210,
        'target_fat_g': 65,
        'sodium_max_mg': 2300,
        'daily_budget': 45,
        'severe_allergens': []
    })
    assert r.status_code == 200, r.text

    meals = [
        {'food_name':'Breakfast','meal_type':'BREAKFAST','calories':400,'protein_g':25,'carbs_g':45,'fat_g':12,'sodium_mg':300},
        {'food_name':'Lunch','meal_type':'LUNCH','calories':900,'protein_g':77,'carbs_g':103,'fat_g':30,'sodium_mg':1020},
    ]
    for meal in meals:
        r = client.post('/api/v1/food-log', headers=h, json=meal)
        assert r.status_code == 200, r.text

    r = client.get('/api/v1/nutrition/today', headers=h)
    assert r.status_code == 200
    d = r.json()['data']
    assert d['totals']['calories'] == 1300
    assert d['daily_state']['remaining_calories'] == 700
    assert d['daily_state']['protein_gap_g'] == 38

    r = client.post('/api/v1/recommendations/for-me', headers=h, json={
        'vendor':'KFC UAE','category':'BURGERS','max_calories':600
    })
    assert r.status_code == 200, r.text
    results = r.json()['data']['results']
    assert results
    assert all(x['vendor'] == 'KFC UAE' for x in results)
    assert any(x['decision'] == 'ELIGIBLE' for x in results)


def test_persisted_severe_allergy_filters_results():
    h = auth_headers('allergy-flow@example.com')
    r = client.patch('/api/v1/users/me', headers=h, json={
        'target_calories':1800, 'target_protein_g':120, 'severe_allergens':['SESAME']
    })
    assert r.status_code == 200
    r = client.post('/api/v1/recommendations/for-me', headers=h, json={'vendor':'KFC UAE','category':'BURGERS'})
    assert r.status_code == 200
    excluded = {x['food_id'] for x in r.json()['data']['excluded']}
    assert 'KFC-AE-014' in excluded
    assert 'KFC-AE-015' in excluded
