
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def reg(email):
    r=client.post('/api/v1/auth/register',json={'email':email,'password':'Password123!','first_name':'T'})
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}

def onboard(h,prefs=None,dislikes=None):
    r=client.post('/api/v1/onboarding/complete',headers=h,json={
        'date_of_birth':'1990-01-01','gender':'MALE','height_cm':175,'weight_kg':80,
        'goal_type':'MAINTAIN','activity_level':'LIGHT','severe_allergens':[],
        'food_preferences':prefs or [],'disliked_foods':dislikes or []
    })
    assert r.status_code==200

def get_item(h,food_id):
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={'allow_modifications':True})
    assert r.status_code==200
    return next(x for x in r.json()['data']['results'] if x['food_id']==food_id)

def test_explicit_chicken_preference_matches_zinger_alias():
    h1=reg('pref-a@example.com'); onboard(h1,prefs=['CHICKEN'])
    h2=reg('pref-b@example.com'); onboard(h2,prefs=[])
    a=get_item(h1,'KFC-AE-014')
    b=get_item(h2,'KFC-AE-014')
    assert a['scores']['preference'] > b['scores']['preference']
    assert 'Matches your stated food preferences' in a['reasons']

def test_dislike_lowers_preference_but_does_not_hard_exclude():
    h=reg('dislike@example.com'); onboard(h,dislikes=['CHICKEN'])
    item=get_item(h,'KFC-AE-014')
    assert item['scores']['preference'] < 80
    assert item['decision'] in {'ELIGIBLE','NEAR_MATCH','MAKE_IT_FIT'}

def test_feedback_and_repetition_learn_incrementally():
    h=reg('learn@example.com'); onboard(h)
    before=get_item(h,'KFC-AE-014')['scores']['preference']
    client.post('/api/v1/recommendations/feedback',headers=h,json={'food_id':'KFC-AE-014','action':'SAVE'})
    client.post('/api/v1/food-log/from-catalog',headers=h,json={'food_id':'KFC-AE-014','meal_type':'LUNCH'})
    after=get_item(h,'KFC-AE-014')['scores']['preference']
    assert after > before

def test_reject_reduces_future_preference_score():
    h=reg('reject@example.com'); onboard(h)
    before=get_item(h,'KFC-AE-014')['scores']['preference']
    client.post('/api/v1/recommendations/feedback',headers=h,json={'food_id':'KFC-AE-014','action':'REJECT'})
    after=get_item(h,'KFC-AE-014')['scores']['preference']
    assert after < before

def test_allergy_still_overrides_preference():
    h=reg('safety-over-pref@example.com')
    client.post('/api/v1/onboarding/complete',headers=h,json={
        'date_of_birth':'1990-01-01','gender':'MALE','height_cm':175,'weight_kg':80,
        'goal_type':'MAINTAIN','activity_level':'LIGHT','severe_allergens':['SESAME'],
        'food_preferences':['CHICKEN'],'disliked_foods':[]
    })
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={'vendor':'KFC UAE','category':'BURGERS'})
    ids={x['food_id'] for x in r.json()['data']['results']}
    assert 'KFC-AE-014' not in ids
