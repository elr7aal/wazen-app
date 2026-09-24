
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def reg(email):
    r=client.post('/api/v1/auth/register',json={'email':email,'password':'Password123!','first_name':'T'})
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}

def test_food_log_today_groups_data_source_for_ui_and_edit_delete():
    h=reg('foodlog-crud@example.com')
    r=client.post('/api/v1/food-log/from-catalog',headers=h,json={
        'food_id':'KFC-AE-014','meal_type':'DINNER','quantity':1
    })
    assert r.status_code==200
    log_id=r.json()['data']['log']['id']

    r=client.get('/api/v1/food-log/today',headers=h)
    assert r.status_code==200
    items=r.json()['data']['items']
    assert len(items)==1
    assert items[0]['meal_type']=='DINNER'
    assert items[0]['calories']==613

    r=client.patch(f'/api/v1/food-log/{log_id}',headers=h,json={
        'meal_type':'LUNCH','calories':600,'protein_g':30
    })
    assert r.status_code==200
    d=r.json()['data']
    assert d['item']['meal_type']=='LUNCH'
    assert d['item']['entry_method']=='USER_EDITED'
    assert d['item']['calories']==600
    assert d['totals']['calories']==600

    r=client.delete(f'/api/v1/food-log/{log_id}',headers=h)
    assert r.status_code==200
    assert r.json()['data']['deleted'] is True
    assert r.json()['data']['daily_state']['remaining_calories']==2000

def test_cannot_edit_another_users_log():
    h1=reg('owner@example.com')
    h2=reg('other@example.com')
    r=client.post('/api/v1/food-log/from-catalog',headers=h1,json={
        'food_id':'KFC-AE-014','meal_type':'DINNER'
    })
    log_id=r.json()['data']['log']['id']
    r=client.patch(f'/api/v1/food-log/{log_id}',headers=h2,json={'calories':1})
    assert r.status_code==404
