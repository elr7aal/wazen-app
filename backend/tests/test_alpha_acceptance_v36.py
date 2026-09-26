from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers(prefix='qa'):
    email=f"{prefix}-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Alpha QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def _set_targets(h,calories=2000,protein=140):
    r=client.patch('/api/v1/users/me',headers=h,json={
        'target_calories':calories,
        'target_protein_g':protein,
        'target_carbs_g':210,
        'target_fat_g':65,
        'target_fiber_g':30,
        'sodium_max_mg':2300,
    })
    assert r.status_code==200


def _add_manual(h,name,calories,meal='LUNCH'):
    r=client.post('/api/v1/food-log',headers=h,json={
        'food_name':name,
        'meal_type':meal,
        'entry_method':'MANUAL',
        'calories':calories,
        'protein_g':20,
        'carbs_g':35,
        'fat_g':10,
        'fiber_g':4,
        'sodium_mg':250,
    })
    assert r.status_code==200
    return r.json()['data']['log_id']


def test_qa_001_daily_math_400_600_300_equals_1300_remaining_700():
    h=_headers('qa001');_set_targets(h)
    _add_manual(h,'Breakfast',400,'BREAKFAST')
    _add_manual(h,'Lunch',600,'LUNCH')
    _add_manual(h,'Snack',300,'SNACK')
    d=client.get('/api/v1/nutrition/today',headers=h).json()['data']
    assert d['totals']['calories']==1300
    assert d['daily_state']['remaining_calories']==700


def test_qa_002_edit_600_to_750_reduces_remaining_by_150():
    h=_headers('qa002');_set_targets(h)
    log_id=_add_manual(h,'Lunch',600,'LUNCH')
    before=client.get('/api/v1/nutrition/today',headers=h).json()['data']['daily_state']['remaining_calories']
    r=client.patch(f'/api/v1/food-log/{log_id}',headers=h,json={'calories':750})
    assert r.status_code==200
    after=r.json()['data']['daily_state']['remaining_calories']
    assert before-after==150


def test_qa_003_delete_300_snack_increases_remaining_by_300():
    h=_headers('qa003');_set_targets(h)
    _add_manual(h,'Meal',600,'LUNCH')
    snack=_add_manual(h,'Snack',300,'SNACK')
    before=client.get('/api/v1/nutrition/today',headers=h).json()['data']['daily_state']['remaining_calories']
    r=client.delete(f'/api/v1/food-log/{snack}',headers=h)
    assert r.status_code==200
    after=r.json()['data']['daily_state']['remaining_calories']
    assert after-before==300


def test_qa_004_severe_milk_allergy_never_reaches_ranked_results():
    h=_headers('qa004')
    p=client.patch('/api/v1/users/me',headers=h,json={'severe_allergens':['MILK']})
    assert p.status_code==200
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'KFC UAE','category':'BURGERS'
    })
    assert r.status_code==200
    data=r.json()['data']
    assert all(x['food_id']!='KFC-AE-007' for x in data['results'])
    assert any(x['food_id']=='KFC-AE-007' and x['reason']=='SEVERE_ALLERGY' for x in data['excluded'])


def test_qa_005_specific_restaurant_craving_preserves_hardees():
    r=client.post('/api/v1/cravings/parse',json={'text':'أبي برغر من هارديز'})
    assert r.status_code==200
    d=r.json()['data']
    assert d['restaurant']=="Hardee's UAE"
    assert d['food_category']=='BURGERS'
    assert d['preserve_restaurant'] is True


def test_qa_006_calorie_constraint_parses_pizza_under_500():
    r=client.post('/api/v1/cravings/parse',json={'text':'أبي بيتزا تحت 500 سعرة'})
    assert r.status_code==200
    d=r.json()['data']
    assert d['food_category']=='PIZZA'
    assert d['max_calories']==500


def test_qa_007_make_it_fit_recalculates_verified_modifiers():
    h=_headers('qa007');_set_targets(h)
    daily=client.get('/api/v1/nutrition/today',headers=h).json()['data']['daily_request']
    r=client.post('/api/v1/recommendations/make-it-fit',headers=h,json={
        'food_id':'KFC-AE-014',
        'daily_state':daily,
        'included_components':['REGULAR_PEPSI_453ML','MEDIUM_FRIES'],
    })
    assert r.status_code==200,r.text
    d=r.json()['data']
    assert d['core_food_unchanged'] is True
    assert len(d['applied_modifications'])==2
    assert d['modified_nutrition']['calories'] < d['base_nutrition']['calories']
    assert round(
        d['modified_nutrition']['calories']-d['base_nutrition']['calories'],1
    )==d['nutrition_delta']['calories']


def test_qa_008_user_override_high_calorie_choice_is_accepted_and_rebalanced():
    h=_headers('qa008');_set_targets(h,calories=500,protein=80)
    r=client.post('/api/v1/food-log/from-catalog',headers=h,json={
        'food_id':'KFC-AE-014','meal_type':'DINNER','quantity':1
    })
    assert r.status_code==200
    assert r.json()['data']['daily_state']['remaining_calories']==0
    reb=client.get('/api/v1/rebalance/for-me',headers=h)
    assert reb.status_code==200
    d=reb.json()['data']
    assert d['user_choice_preserved'] is True
    assert d['strategy']=='LIGHTER_NEXT_OPTIONS'
    assert 'اختيارك محفوظ' in d['message']


def test_qa_009_missing_sodium_with_strict_limit_is_not_called_low_sodium():
    h=_headers('qa009')
    lim=client.put('/api/v1/health-limits',headers=h,json={
        'nutrient_code':'SODIUM_MG',
        'limit_type':'MAX',
        'value':500,
        'unit':'mg',
        'severity':'HARD',
        'source_type':'USER',
        'active':True,
    })
    assert lim.status_code==200
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'Carrefour UAE','category':'OATS'
    })
    assert r.status_code==200
    data=r.json()['data']
    row=next(x for x in data['excluded'] if x['food_id']=='GR-AE-003')
    assert row['reason']=='HEALTH_LIMIT'
    assert 'MISSING_SODIUM_MG' in row['details']
    assert all(x['food_id']!='GR-AE-003' for x in data['results'])


def test_qa_010_source_confidence_and_verification_are_exposed():
    r=client.get('/api/v1/foods/KFC-AE-014')
    assert r.status_code==200
    d=r.json()['data']
    assert d['source_confidence']=='VERIFIED'
    assert d['source_name']
    assert d['source_reference']
    assert d['source_verified_at'] is not None
