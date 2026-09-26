from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_unknown_nutrients_propagate_and_explicit_zero_is_preserved():
    response = client.post('/api/v1/auth/register', json={
        'email': f'unknown-{uuid4().hex}@example.com',
        'password': 'StrongPass123!', 'first_name': 'QA'})
    headers = {'Authorization': 'Bearer ' + response.json()['data']['access_token']}
    client.patch('/api/v1/users/me', headers=headers, json={'target_fiber_g': 30, 'sodium_max_mg': 2300})
    meal = {'food_name': 'Manual unknown', 'meal_type': 'LUNCH', 'entry_method': 'MANUAL', 'calories': 100}
    response = client.post('/api/v1/food-log', headers=headers, json=meal)
    assert response.status_code == 200, response.text
    log_id = response.json()['data']['log_id']
    data = client.get('/api/v1/nutrition/today', headers=headers).json()['data']
    for key in ('fiber_g', 'sodium_mg'):
        assert data['totals'][key] is None
    assert data['daily_state']['fiber_remaining_g'] is None
    assert data['daily_state']['sodium_remaining_mg'] is None
    response = client.patch(f'/api/v1/food-log/{log_id}', headers=headers,
                            json={'fiber_g': 0, 'sodium_mg': 0})
    assert response.status_code == 200
    data = client.get('/api/v1/nutrition/today', headers=headers).json()['data']
    assert data['totals']['fiber_g'] == 0
    assert data['totals']['sodium_mg'] == 0
    assert data['daily_state']['sodium_remaining_mg'] == 2300
    # One unknown entry prevents a misleading complete daily total.
    client.post('/api/v1/food-log', headers=headers, json=meal)
    data = client.get('/api/v1/nutrition/today', headers=headers).json()['data']
    assert data['totals']['fiber_g'] is None
    assert data['totals']['sodium_mg'] is None


def test_make_it_fit_preserves_unknown_base_and_modifier_sodium():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db import Base
    from app.models.db_models import FoodItem, FoodNutrition, FoodModifier
    from app.models.schemas import MakeItFitRequest, DailyStateRequest
    from app.services.make_it_fit import make_it_fit
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        item = FoodItem(id='test-food', name_en='Test', food_type='RESTAURANT', vendor_name='KFC')
        item.nutrition = FoodNutrition(calories=100, sodium_mg=None)
        db.add(item)
        modifier = FoodModifier(id='KFC-MOD-001', vendor_name='KFC', modifier_group='DRINK',
            name_en='Drink change', action='REPLACE', sodium_delta_mg=None)
        db.add(modifier)
        db.commit()
        req = MakeItFitRequest(food_id=item.id, included_components=[],
            daily_state=DailyStateRequest(target_calories=2000, consumed_calories=0,
                                         target_protein_g=100, consumed_protein_g=0))
        result = make_it_fit(db, req)
        assert result['base_nutrition']['sodium_mg'] is None
        assert result['modified_nutrition']['sodium_mg'] is None
        assert result['nutrition_delta']['sodium_mg'] is None
        item.nutrition.sodium_mg = 100
        db.commit()
        req.included_components = ['REGULAR_PEPSI_453ML']
        assert make_it_fit(db, req)['modified_nutrition']['sodium_mg'] is None
        modifier.sodium_delta_mg = 0
        db.commit()
        assert make_it_fit(db, req)['modified_nutrition']['sodium_mg'] == 100
