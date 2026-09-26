
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def reg(email):
    r=client.post('/api/v1/auth/register',json={'email':email,'password':'Password123!','first_name':'T'})
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}

def onboard(h):
    r=client.post('/api/v1/onboarding/complete',headers=h,json={
        'date_of_birth':'1990-01-01','gender':'MALE','height_cm':175,'weight_kg':80,
        'target_weight_kg':75,'goal_type':'MAINTAIN','activity_level':'LIGHT',
        'daily_budget':45,'severe_allergens':['PEANUT'],'food_preferences':['CHICKEN'],
        'disliked_foods':['MUSHROOM']
    })
    assert r.status_code==200

def test_recalculate_plan_after_goal_change():
    h=reg('profile-plan@example.com'); onboard(h)
    before=client.get('/api/v1/users/me',headers=h).json()['data']['profile']['target_calories']
    r=client.post('/api/v1/profile/recalculate-plan',headers=h,json={'goal_type':'LOSE','weight_kg':78})
    assert r.status_code==200
    d=r.json()['data']
    assert d['profile']['goal_type']=='LOSE'
    assert d['profile']['weight_kg']==78
    assert d['targets']['target_calories'] < before

def test_profile_insights_separate_safety_and_preferences():
    h=reg('profile-insights@example.com'); onboard(h)
    r=client.get('/api/v1/profile/insights',headers=h)
    assert r.status_code==200
    d=r.json()['data']
    assert d['hard_exclusions']==['PEANUT']
    assert d['stated_preferences']==['CHICKEN']
    assert d['stated_dislikes']==['MUSHROOM']
    assert len(d['explanation_ar'])>=4

def test_profile_insights_learns_rejection_and_repeat():
    h=reg('profile-learn@example.com'); onboard(h)
    for _ in range(2):
        client.post('/api/v1/food-log/from-catalog',headers=h,json={'food_id':'KFC-AE-014','meal_type':'LUNCH'})
    client.post('/api/v1/recommendations/feedback',headers=h,json={'food_id':'MCD-AE-007','action':'REJECT'})
    d=client.get('/api/v1/profile/insights',headers=h).json()['data']
    assert any(x['food_id']=='KFC-AE-014' for x in d['learned_positive'])
    assert any(x['food_id']=='MCD-AE-007' for x in d['learned_negative'])
