
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def reg(email):
    r = client.post('/api/v1/auth/register', json={
        'email': email, 'password': 'Password123!', 'first_name': 'T'
    })
    assert r.status_code == 200
    return {'Authorization': f"Bearer {r.json()['data']['access_token']}"}

def test_rebalance_uses_persisted_day_and_returns_next_options():
    h = reg('rebalance@example.com')
    client.patch('/api/v1/users/me', headers=h, json={
        'target_calories': 2000, 'target_protein_g': 140,
        'target_carbs_g': 210, 'target_fat_g': 65
    })
    # Log Zinger
    r = client.post('/api/v1/food-log/from-catalog', headers=h, json={
        'food_id': 'KFC-AE-014', 'meal_type': 'DINNER', 'quantity': 1
    })
    assert r.status_code == 200

    r = client.get('/api/v1/rebalance/for-me', headers=h)
    assert r.status_code == 200
    d = r.json()['data']
    assert d['daily_state']['remaining_calories'] == 1387
    assert d['daily_state']['protein_gap_g'] == 108.5
    assert isinstance(d['next_options'], list)
    assert len(d['next_options']) > 0
    assert 'باقي' in d['message'] or 'يومك' in d['message']

def test_rebalance_after_modified_meal_reads_modified_snapshot():
    h = reg('rebalance-modified@example.com')
    client.patch('/api/v1/users/me', headers=h, json={
        'target_calories': 1000, 'target_protein_g': 100
    })
    r = client.post('/api/v1/food-log/from-modified-catalog', headers=h, json={
        'food_id':'KFC-AE-014',
        'meal_type':'DINNER',
        'included_components':['REGULAR_PEPSI_453ML']
    })
    assert r.status_code == 200
    assert round(r.json()['data']['log']['calories'],1) == 415.7

    r = client.get('/api/v1/rebalance/for-me', headers=h)
    assert r.status_code == 200
    d = r.json()['data']
    assert round(d['daily_state']['remaining_calories'],1) == 584.3
