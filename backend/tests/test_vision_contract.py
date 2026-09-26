from fastapi.testclient import TestClient
from app.main import app
from app.services import vision

client=TestClient(app)

def reg(email):
    r=client.post('/api/v1/auth/register',json={'email':email,'password':'Password123!','first_name':'T'})
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}

def test_vision_fallback_without_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    h=reg('vision-fallback@example.com')
    r=client.post('/api/v1/food-log/analyze-image',headers=h,json={
        'image_base64':'YWJjZGVmZ2g=','user_caption':'زينجر KFC','meal_type':'DINNER'
    })
    assert r.status_code==200
    d=r.json()['data']
    assert d['analysis_provider']=='NOT_CONFIGURED'
    assert d['status']=='REVIEW_REQUIRED'
    assert d['vision_result'] is None

def test_output_text_extraction():
    payload={'output':[{'content':[{'type':'output_text','text':'{"items":[]}'}]}]}
    assert vision._extract_output_text(payload)=='{"items":[]}'

def test_fenced_json_parser():
    raw="```json\n{\"items\":[]}\n```"
    parsed=vision.re_fence(raw)
    assert parsed=='{"items":[]}'

def test_image_analysis_does_not_log(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    h=reg('vision-no-log@example.com')
    before=client.get('/api/v1/food-log/today',headers=h).json()['data']['items']
    client.post('/api/v1/food-log/analyze-image',headers=h,json={'image_base64':'YWJjZGVmZ2g=','meal_type':'SNACK'})
    after=client.get('/api/v1/food-log/today',headers=h).json()['data']['items']
    assert before==after==[]
