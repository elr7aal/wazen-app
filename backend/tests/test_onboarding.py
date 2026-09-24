from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.services.onboarding import calculate_targets
from app.models.schemas import OnboardingCompleteRequest

client=TestClient(app)

def reg(email):
    r=client.post('/api/v1/auth/register',json={'email':email,'password':'Password123!','first_name':'T'})
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}

def payload():
    return {
        'first_name':'Ali',
        'date_of_birth':'1990-01-01',
        'gender':'MALE',
        'height_cm':175,
        'weight_kg':85,
        'target_weight_kg':78,
        'goal_type':'LOSE',
        'activity_level':'LIGHT',
        'daily_budget':45,
        'severe_allergens':['PEANUT'],
        'food_preferences':['CHICKEN','RICE'],
        'disliked_foods':['MUSHROOM']
    }

def test_new_user_starts_incomplete_then_completes():
    h=reg('onboard@example.com')
    r=client.get('/api/v1/onboarding/status',headers=h)
    assert r.json()['data']['complete'] is False

    r=client.post('/api/v1/onboarding/complete',headers=h,json=payload())
    assert r.status_code==200
    d=r.json()['data']
    assert d['complete'] is True
    assert d['targets']['target_calories'] > 1200
    assert d['targets']['target_protein_g'] >= 60
    assert d['profile']['severe_allergens']==['PEANUT']
    assert d['profile']['onboarding_complete'] is True

    r=client.get('/api/v1/onboarding/status',headers=h)
    assert r.json()['data']['complete'] is True

def test_calorie_target_changes_with_goal():
    base=payload()
    lose=calculate_targets(OnboardingCompleteRequest(**base))
    base['goal_type']='GAIN'
    gain=calculate_targets(OnboardingCompleteRequest(**base))
    assert gain['target_calories'] > lose['target_calories']

def test_age_and_profile_inputs_persist():
    h=reg('onboard-profile@example.com')
    client.post('/api/v1/onboarding/complete',headers=h,json=payload())
    d=client.get('/api/v1/users/me',headers=h).json()['data']['profile']
    assert d['date_of_birth']=='1990-01-01'
    assert d['gender']=='MALE'
    assert d['food_preferences']==['CHICKEN','RICE']
    assert d['disliked_foods']==['MUSHROOM']
