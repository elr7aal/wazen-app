from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def _headers():
    email=f"daily-v27-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Daily QA'
    })
    assert r.status_code==200
    h={'Authorization':f"Bearer {r.json()['data']['access_token']}"}
    p=client.patch('/api/v1/users/me',headers=h,json={
        'target_calories':2000,
        'target_protein_g':140,
        'target_carbs_g':210,
        'target_fat_g':65,
        'target_fiber_g':30,
        'sodium_max_mg':2300,
    })
    assert p.status_code==200
    return h


def _add(h,name,calories,fiber=0):
    r=client.post('/api/v1/food-log',headers=h,json={
        'food_name':name,
        'meal_type':'LUNCH',
        'entry_method':'MANUAL',
        'calories':calories,
        'protein_g':20,
        'carbs_g':40,
        'fat_g':10,
        'fiber_g':fiber,
        'sodium_mg':300,
    })
    assert r.status_code==200,r.text
    return r.json()['data']['log_id']


def test_edit_600_to_750_reduces_remaining_by_150():
    h=_headers()
    log_id=_add(h,'Lunch',600,8)
    before=client.get('/api/v1/nutrition/today',headers=h).json()['data']['daily_state']['remaining_calories']
    assert before==1400

    r=client.patch(f'/api/v1/food-log/{log_id}',headers=h,json={'calories':750})
    assert r.status_code==200
    after=r.json()['data']['daily_state']['remaining_calories']
    assert after==1250
    assert before-after==150


def test_fiber_aggregates_and_gap_updates():
    h=_headers()
    _add(h,'Fiber meal A',400,8)
    _add(h,'Fiber meal B',500,7)
    data=client.get('/api/v1/nutrition/today',headers=h).json()['data']
    assert data['totals']['fiber_g']==15
    assert data['daily_state']['fiber_remaining_g']==15


def test_activity_credit_increases_remaining_and_delete_reverses_it():
    h=_headers()
    _add(h,'Meal',600,5)
    base=client.get('/api/v1/nutrition/today',headers=h).json()['data']['daily_state']
    assert base['remaining_calories']==1400
    assert base['activity_credit']==0

    r=client.post('/api/v1/activity-log',headers=h,json={
        'calories_credit':250,
        'source':'WORKOUT',
        'note':'QA workout',
    })
    assert r.status_code==200
    activity_id=r.json()['data']['item']['id']
    state=r.json()['data']['daily_state']
    assert state['activity_credit']==250
    assert state['remaining_calories']==1650

    deleted=client.delete(f'/api/v1/activity-log/{activity_id}',headers=h)
    assert deleted.status_code==200
    state2=deleted.json()['data']['daily_state']
    assert state2['activity_credit']==0
    assert state2['remaining_calories']==1400


def test_activity_today_lists_credit():
    h=_headers()
    client.post('/api/v1/activity-log',headers=h,json={
        'calories_credit':120,'source':'MANUAL','note':'Walk'
    })
    client.post('/api/v1/activity-log',headers=h,json={
        'calories_credit':80,'source':'PHONE','note':'Steps'
    })
    r=client.get('/api/v1/activity-log/today',headers=h)
    assert r.status_code==200
    data=r.json()['data']
    assert len(data['items'])==2
    assert data['activity_credit']==200
