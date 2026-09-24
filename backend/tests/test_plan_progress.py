from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _user():
    email = f"plan-{uuid4().hex[:8]}@example.com"
    r = client.post('/api/v1/auth/register', json={
        'email': email,
        'password': 'StrongPass123',
        'first_name': 'Plan QA',
    })
    assert r.status_code == 200
    token = r.json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_weekly_plan_has_seven_days_and_meals():
    h = _user()
    r = client.get('/api/v1/plan/week', headers=h)
    assert r.status_code == 200
    data = r.json()['data']
    assert len(data['days']) == 7
    assert all(len(day['items']) == 4 for day in data['days'])
    assert all(day['total_calories'] > 0 for day in data['days'])


def test_rebalance_single_day_keeps_week_shape():
    h = _user()
    week = client.get('/api/v1/plan/week', headers=h).json()['data']
    d = week['days'][0]['date']
    r = client.post(f'/api/v1/plan/day/{d}/rebalance', headers=h)
    assert r.status_code == 200
    data = r.json()['data']
    assert len(data['days']) == 7
    target = next(x for x in data['days'] if x['date'] == d)
    assert len(target['items']) == 4


def test_progress_tracks_food_and_weight():
    h = _user()
    profile = client.patch('/api/v1/users/me', headers=h, json={
        'weight_kg': 81.5,
        'target_calories': 2000,
        'target_protein_g': 100,
    })
    assert profile.status_code == 200

    add = client.post('/api/v1/food-log', headers=h, json={
        'food_name': 'Progress Test Meal',
        'meal_type': 'LUNCH',
        'entry_method': 'MANUAL',
        'calories': 1800,
        'protein_g': 95,
        'carbs_g': 150,
        'fat_g': 60,
        'sodium_mg': 900,
    })
    assert add.status_code == 200

    r = client.get('/api/v1/progress', headers=h, params={'range': 'week'})
    assert r.status_code == 200
    data = r.json()['data']
    assert data['range_days'] == 7
    assert data['tracked_days'] >= 1
    assert data['goal_days'] >= 1
    assert data['average_protein_g'] >= 95
    assert data['weight_trend']
    assert data['weight_trend'][-1]['weight_kg'] == 81.5
