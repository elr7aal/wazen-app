import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.main import app
from app.models.db_models import (
    User, UserProfile, FoodLog, RecommendationFeedback, WeeklyPlanItem,
    WeightHistory, AuthSession, PasswordResetToken, GoalHistory,
    UserPreferenceSetting, HealthLimit, FavoriteMeal, ActivityLog,
    RecommendationExclusionLog, RecommendationDecisionLog, IdempotencyRecord,
)

client=TestClient(app)
PASSWORD='StrongPass123!'


def _register():
    email=f"privacy-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':PASSWORD,'first_name':'Privacy QA'
    })
    assert r.status_code==200
    data=r.json()['data']
    return email,data,{'Authorization':f"Bearer {data['access_token']}"}


def _seed_user_data(h):
    assert client.post('/api/v1/food-log',headers=h,json={
        'food_name':'Privacy Meal','meal_type':'LUNCH','entry_method':'MANUAL',
        'calories':410,'protein_g':28,'carbs_g':40,'fat_g':14,'fiber_g':5,'sodium_mg':420,
    }).status_code==200
    assert client.put('/api/v1/preferences',headers=h,json={
        'target_type':'TERM','target_value':'CHICKEN','level':'LIKE'
    }).status_code==200
    assert client.put('/api/v1/health-limits',headers=h,json={
        'nutrient_code':'SODIUM_MG','limit_type':'MAX','value':1800,'unit':'mg',
        'severity':'SOFT','source_type':'USER','active':True,
    }).status_code==200
    assert client.post('/api/v1/activity-log',headers=h,json={
        'calories_credit':120,'source':'MANUAL','note':'Privacy QA walk'
    }).status_code==200
    assert client.post('/api/v1/recommendations/feedback',headers=h,json={
        'food_id':'MCD-AE-001','action':'SAVE'
    }).status_code==200


def test_export_contains_user_data_but_no_credentials_or_hashes():
    email,data,h=_register()
    _seed_user_data(h)

    r=client.get('/api/v1/users/me/export',headers=h)
    assert r.status_code==200, r.text
    exported=r.json()['data']
    assert exported['account']['email']==email
    assert exported['food_logs']
    assert exported['preferences']
    assert exported['health_limits']
    assert exported['activity_logs']
    assert exported['recommendation_feedback']
    assert exported['security']['credentials_exported'] is False

    raw=json.dumps(exported)
    assert 'password_hash' not in raw
    assert 'refresh_token_hash' not in raw
    assert 'token_hash' not in raw
    assert PASSWORD not in raw
    assert data['refresh_token'] not in raw


def test_delete_account_rejects_wrong_password():
    email,_,h=_register()
    r=client.request('DELETE','/api/v1/users/me',headers=h,json={
        'password':'WrongPassword999!','confirm':'DELETE'
    })
    assert r.status_code==401
    login=client.post('/api/v1/auth/login',json={'email':email,'password':PASSWORD})
    assert login.status_code==200


def test_delete_account_purges_user_rows_and_invalidates_credentials():
    email,data,h=_register()
    user_id=data['user_id']
    refresh=data['refresh_token']
    _seed_user_data(h)

    # Create additional history / planning data.
    client.patch('/api/v1/users/me',headers=h,json={'weight_kg':81.2})
    client.get('/api/v1/plan/week',headers=h)
    client.get('/api/v1/recommendations/for-me',headers=h)

    r=client.request('DELETE','/api/v1/users/me',headers=h,json={
        'password':PASSWORD,'confirm':'DELETE'
    })
    assert r.status_code==200, r.text
    assert r.json()['data']['deleted'] is True

    assert client.get('/api/v1/users/me',headers=h).status_code==401
    assert client.post('/api/v1/auth/refresh',json={'refresh_token':refresh}).status_code==401
    assert client.post('/api/v1/auth/login',json={'email':email,'password':PASSWORD}).status_code==401

    models=[
        UserProfile,FoodLog,RecommendationFeedback,WeeklyPlanItem,WeightHistory,
        AuthSession,PasswordResetToken,GoalHistory,UserPreferenceSetting,HealthLimit,
        FavoriteMeal,ActivityLog,RecommendationExclusionLog,RecommendationDecisionLog,
        IdempotencyRecord,
    ]
    with SessionLocal() as db:
        assert db.get(User,user_id) is None
        for model in models:
            count=db.scalar(select(func.count()).select_from(model).where(model.user_id==user_id))
            assert count==0, model.__tablename__
