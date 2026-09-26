from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"nlp-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'NLP QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def test_arabic_multi_item_parse_requires_preview_and_does_not_save():
    h=_headers()
    before=client.get('/api/v1/food-log/today',headers=h).json()['data']['items']
    assert before==[]

    r=client.post('/api/v1/food-log/parse-text',headers=h,json={
        'text':'مجبوس دجاج وكوب لبن',
        'meal_type':'LUNCH',
    })
    assert r.status_code==200, r.text
    data=r.json()['data']
    assert data['preview_required'] is True
    assert data['auto_saved'] is False
    assert len(data['items'])==2
    assert data['items'][0]['editable'] is True
    assert data['items'][1]['editable'] is True
    assert data['items'][1]['estimated_unit']=='CUP'

    after=client.get('/api/v1/food-log/today',headers=h).json()['data']['items']
    assert after==[]


def test_portion_estimates_are_exposed_for_editing():
    h=_headers()
    r=client.post('/api/v1/food-log/parse-text',headers=h,json={
        'text':'نص برغر و2 كوب لبن',
        'meal_type':'DINNER',
    })
    assert r.status_code==200
    items=r.json()['data']['items']
    assert len(items)==2
    assert items[0]['estimated_quantity']==0.5
    assert items[1]['estimated_quantity']==2
    assert items[1]['estimated_unit']=='CUP'


def test_english_multi_item_parse():
    h=_headers()
    r=client.post('/api/v1/food-log/parse-text',headers=h,json={
        'text':'burger and fries',
        'meal_type':'DINNER',
    })
    assert r.status_code==200
    data=r.json()['data']
    assert len(data['items'])==2
    assert data['preview_required'] is True
