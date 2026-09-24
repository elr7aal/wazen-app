
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def reg(email):
    r=client.post('/api/v1/auth/register',json={'email':email,'password':'Password123!','first_name':'T'})
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}

def test_options_are_verified():
    h=reg('mif-options@example.com')
    r=client.get('/api/v1/foods/KFC-AE-014/make-it-fit-options',headers=h)
    assert r.status_code==200
    opts=r.json()['data']['options']
    assert len(opts)==5
    assert all(o['confidence']=='VERIFIED' for o in opts)

def test_non_kfc_has_no_unverified_options():
    h=reg('mif-nonkfc@example.com')
    r=client.get('/api/v1/foods/MCD-AE-007/make-it-fit-options',headers=h)
    assert r.status_code==200
    assert r.json()['data']['options']==[]

def test_modified_log_uses_verified_delta():
    h=reg('mif-log@example.com')
    client.patch('/api/v1/users/me',headers=h,json={'target_calories':2000,'target_protein_g':140})
    r=client.post('/api/v1/food-log/from-modified-catalog',headers=h,json={
        'food_id':'KFC-AE-014','meal_type':'DINNER','included_components':['REGULAR_PEPSI_453ML']
    })
    assert r.status_code==200
    d=r.json()['data']
    assert round(d['log']['calories'],1)==415.7
    assert d['make_it_fit']['calories_saved']==197.3
    assert d['daily_state']['remaining_calories']==1584.3

def test_no_selected_components_keeps_base():
    h=reg('mif-base@example.com')
    r=client.post('/api/v1/food-log/from-modified-catalog',headers=h,json={
        'food_id':'KFC-AE-014','meal_type':'DINNER','included_components':[]
    })
    assert r.status_code==200
    assert r.json()['data']['log']['calories']==613
