
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _register(email):
    r = client.post('/api/v1/auth/register', json={
        'email': email, 'password': 'Password123!', 'first_name': 'Tester'
    })
    assert r.status_code == 200
    return r.json()['data']['access_token']


def test_catalog_item_can_be_logged_and_updates_daily_state():
    token = _register('cataloglog@example.com')
    h = {'Authorization': f'Bearer {token}'}

    r = client.patch('/api/v1/users/me', headers=h, json={
        'target_calories': 2000, 'target_protein_g': 140
    })
    assert r.status_code == 200

    r = client.post('/api/v1/food-log/from-catalog', headers=h, json={
        'food_id': 'KFC-AE-014', 'meal_type': 'DINNER', 'quantity': 1
    })
    assert r.status_code == 200
    d = r.json()['data']
    assert d['log']['food_name'] == 'Zinger Sandwich'
    assert d['log']['calories'] == 613
    assert d['daily_totals']['calories'] == 613
    assert d['daily_state']['remaining_calories'] == 1387


def test_quantity_multiplies_catalog_nutrition():
    token = _register('quantity@example.com')
    h = {'Authorization': f'Bearer {token}'}
    r = client.post('/api/v1/food-log/from-catalog', headers=h, json={
        'food_id': 'KFC-AE-006', 'meal_type': 'SNACK', 'quantity': 2
    })
    assert r.status_code == 200
    d = r.json()['data']
    assert d['log']['calories'] == 257.0
    assert d['log']['protein_g'] == 26.6


def test_golden_flow_parses_craving_and_recommends_from_catalog():
    token = _register('goldenflow@example.com')
    h = {'Authorization': f'Bearer {token}'}
    client.patch('/api/v1/users/me', headers=h, json={
        'target_calories': 2000, 'target_protein_g': 140,
        'severe_allergens': []
    })

    r = client.post('/api/v1/golden-flow', headers=h, json={
        'craving_text': 'أبي برغر من KFC تحت 600 سعرة',
        'meal_type': 'DINNER'
    })
    assert r.status_code == 200
    d = r.json()['data']
    assert d['parsed_intent']['restaurant'] == 'KFC UAE'
    assert d['parsed_intent']['food_category'] == 'BURGERS'
    assert d['parsed_intent']['max_calories'] == 600
    assert len(d['recommendations']['results']) > 0
    assert all(x['vendor'] == 'KFC UAE' for x in d['recommendations']['results'])


def test_golden_flow_can_log_choice_then_recommend_again():
    token = _register('flowlog@example.com')
    h = {'Authorization': f'Bearer {token}'}
    client.patch('/api/v1/users/me', headers=h, json={
        'target_calories': 2000, 'target_protein_g': 140
    })

    r = client.post('/api/v1/golden-flow', headers=h, json={
        'craving_text': 'أبي برغر من KFC',
        'meal_type': 'DINNER',
        'auto_log_food_id': 'KFC-AE-014',
        'quantity': 1
    })
    assert r.status_code == 200
    d = r.json()['data']
    assert d['logged']['food_id'] == 'KFC-AE-014'
    assert d['daily_totals']['calories'] == 613
    assert d['daily_state']['remaining_calories'] == 1387
