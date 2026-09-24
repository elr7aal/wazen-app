
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def reg(email):
    r=client.post('/api/v1/auth/register',json={'email':email,'password':'Password123!','first_name':'T'})
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}

def test_text_input_returns_reviewable_catalog_matches():
    h=reg('text-input@example.com')
    r=client.post('/api/v1/food-log/parse-text',headers=h,json={'text':'أكلت زينجر من KFC','meal_type':'DINNER'})
    assert r.status_code==200
    d=r.json()['data']
    assert d['status']=='MATCHES_FOUND'
    assert any(x['food_id']=='KFC-AE-014' for x in d['candidates'])

def test_image_endpoint_never_fakes_vision_analysis():
    h=reg('image-input@example.com')
    r=client.post('/api/v1/food-log/analyze-image',headers=h,json={
        'image_base64':'YWJjZGVmZ2g=','user_caption':'زينجر KFC','meal_type':'DINNER'
    })
    assert r.status_code==200
    d=r.json()['data']
    assert d['analysis_provider']=='NOT_CONFIGURED'
    assert d['status']=='REVIEW_REQUIRED'
    assert 'note' in d

def test_unknown_barcode_is_reviewable():
    h=reg('barcode-input@example.com')
    r=client.get('/api/v1/foods/barcode/0000000000000',headers=h)
    assert r.status_code==200
    d=r.json()['data']
    assert d['found'] is False
    assert d['allow_submission'] is True
