from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.services.vision_review import build_vision_review

client=TestClient(app)


def reg(email):
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'Password123!','first_name':'Vision QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def test_vision_review_maps_candidates_and_requires_low_confidence_confirmation():
    fake={
        'description_ar':'وجبة برغر وبطاطس',
        'overall_confidence':0.62,
        'items':[
            {
                'name':'Big Mac',
                'name_ar':'بيج ماك',
                'estimated_quantity':1,
                'estimated_unit':'serving',
                'estimated_calories':550,
                'estimated_protein_g':23,
                'estimated_carbs_g':46,
                'estimated_fat_g':30,
                'confidence':0.91,
            },
            {
                'name':'Fries',
                'name_ar':'بطاطس',
                'estimated_quantity':1.5,
                'estimated_unit':'serving',
                'estimated_calories':320,
                'estimated_protein_g':4,
                'estimated_carbs_g':42,
                'estimated_fat_g':15,
                'confidence':0.42,
            },
        ],
    }
    with SessionLocal() as db:
        review=build_vision_review(db,fake)

    assert review['preview_required'] is True
    assert review['auto_saved'] is False
    assert len(review['items'])==2
    assert review['items'][0]['requires_confirmation'] is False
    assert review['items'][1]['requires_confirmation'] is True
    assert review['items'][1]['estimated_quantity']==1.5
    assert any(x['food_id']=='MCD-AE-007' for x in review['items'][0]['candidates'])


def test_no_provider_returns_caption_review_without_logging(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    h=reg('vision-caption-v26@example.com')

    r=client.post('/api/v1/food-log/analyze-image',headers=h,json={
        'image_base64':'YWJjZGVmZ2g=',
        'user_caption':'بيج ماك',
        'meal_type':'DINNER',
    })
    assert r.status_code==200
    data=r.json()['data']
    assert data['analysis_provider']=='NOT_CONFIGURED'
    assert data['image_analyzed'] is False
    assert data['preview_required'] is True
    assert data['auto_saved'] is False
    assert data['items']

    day=client.get('/api/v1/food-log/today',headers=h).json()['data']
    assert day['items']==[]
