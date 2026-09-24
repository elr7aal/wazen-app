from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _ids(q):
    r=client.get('/api/v1/foods/search',params={'q':q,'limit':100})
    assert r.status_code==200, r.text
    return {x['food_id'] for x in r.json()['data']['items']}


def test_burger_synonyms_return_same_family():
    ar1=_ids('برغر')
    ar2=_ids('برجر')
    en=_ids('burger')
    common=ar1 & ar2 & en
    assert common
    assert 'MCD-AE-001' in common


def test_catalog_nutrition_filters():
    r=client.get('/api/v1/foods/search',params={
        'vendor':"McDonald's UAE",
        'category':'BURGERS',
        'max_sodium_mg':500,
        'min_protein_g':10,
        'limit':100,
    })
    assert r.status_code==200
    items=r.json()['data']['items']
    assert items
    assert all(x['nutrition']['sodium_mg'] is not None and x['nutrition']['sodium_mg']<=500 for x in items)
    assert all(x['nutrition']['protein_g'] is not None and x['nutrition']['protein_g']>=10 for x in items)


def test_catalog_food_type_filter():
    r=client.get('/api/v1/foods/search',params={'food_type':'GROCERY','limit':100})
    assert r.status_code==200
    items=r.json()['data']['items']
    assert items
    assert all(x['food_type']=='GROCERY' for x in items)


def test_brand_filter():
    r=client.get('/api/v1/foods/search',params={'brand':"McDonald's UAE",'limit':100})
    assert r.status_code==200
    items=r.json()['data']['items']
    assert items
    assert all((x['brand'] or '')=="McDonald's UAE" for x in items)
