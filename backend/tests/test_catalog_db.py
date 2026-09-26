from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_grocery_is_in_same_catalog():
    r = client.get('/api/v1/foods/search', params={'vendor':'Carrefour UAE','limit':50})
    assert r.status_code == 200
    items = r.json()['data']['items']
    assert len(items) >= 10
    assert any(x['food_type'] == 'GROCERY' for x in items)


def test_food_detail_exposes_source_and_allergens():
    r = client.get('/api/v1/foods/KFC-AE-014')
    assert r.status_code == 200
    d = r.json()['data']
    assert d['name'] == 'Zinger Sandwich'
    assert d['nutrition']['calories'] == 613
    assert 'SESAME' in d['allergens']
    assert d['source_confidence'] == 'VERIFIED'
