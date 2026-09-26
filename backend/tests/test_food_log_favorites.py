from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"logfav-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Log QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def _add(h,calories=400,protein=25):
    r=client.post('/api/v1/food-log',headers=h,json={
        'food_name':'Favorite QA Meal',
        'meal_type':'LUNCH',
        'entry_method':'MANUAL',
        'calories':calories,
        'protein_g':protein,
        'carbs_g':45,
        'fat_g':12,
        'sodium_mg':300,
    })
    assert r.status_code==200
    return r.json()['data']['log_id']


def test_duplicate_food_log_updates_totals():
    h=_headers()
    log_id=_add(h,400,25)
    r=client.post(f'/api/v1/food-log/{log_id}/duplicate',headers=h)
    assert r.status_code==200, r.text
    data=r.json()['data']
    assert data['item']['entry_method']=='DUPLICATED'
    assert data['totals']['calories']==800
    assert data['totals']['protein_g']==50


def test_favorite_log_roundtrip_and_relog():
    h=_headers()
    log_id=_add(h,350,30)

    fav=client.post(f'/api/v1/food-log/{log_id}/favorite',headers=h)
    assert fav.status_code==200
    fav_id=fav.json()['data']['favorite']['id']
    assert fav.json()['data']['created'] is True

    duplicate_fav=client.post(f'/api/v1/food-log/{log_id}/favorite',headers=h)
    assert duplicate_fav.status_code==200
    assert duplicate_fav.json()['data']['created'] is False

    listing=client.get('/api/v1/food-log/favorites',headers=h)
    assert listing.status_code==200
    assert listing.json()['data']['count']==1

    relog=client.post(
        f'/api/v1/food-log/favorites/{fav_id}/log',
        headers=h,
        json={'meal_type':'DINNER'},
    )
    assert relog.status_code==200
    data=relog.json()['data']
    assert data['item']['entry_method']=='FAVORITE'
    assert data['item']['meal_type']=='DINNER'
    assert data['totals']['calories']==700
