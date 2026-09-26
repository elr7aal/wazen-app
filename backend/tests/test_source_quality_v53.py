from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.db_models import FoodDataSource, FoodItem, FoodNutrition

client=TestClient(app)
ADMIN_HEADERS={
    'X-WAZEN-ADMIN-KEY':'test-admin-key',
    'X-WAZEN-ADMIN-ACTOR':'quality-qa',
}


def _auth_headers():
    email=f"quality-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Quality QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def test_seed_food_exposes_fresh_source_metadata():
    r=client.get('/api/v1/foods/MCD-AE-001')
    assert r.status_code==200
    data=r.json()['data']
    assert data['source_freshness']=='FRESH'
    assert data['source_age_days'] is not None
    assert data['source_age_days'] <= 180


def test_recommendations_include_source_freshness():
    h=_auth_headers()
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':"McDonald's UAE",
        'category':'BURGERS',
    })
    assert r.status_code==200, r.text
    items=r.json()['data']['results']
    assert items
    assert all('source_freshness' in x for x in items)
    assert all('source_age_days' in x for x in items)


def test_admin_quality_report_flags_stale_and_missing_data():
    stale_id=f"QA-STALE-{uuid4().hex[:6]}"
    missing_id=f"QA-MISSING-{uuid4().hex[:6]}"
    now=datetime.now(timezone.utc).replace(tzinfo=None)

    with SessionLocal() as db:
        stale=FoodItem(
            id=stale_id,
            name_en='Stale QA Meal',
            food_type='RESTAURANT',
            vendor_name='QA Vendor',
            category='QA',
            status='ACTIVE',
        )
        db.add(stale)
        db.add(FoodNutrition(
            food_id=stale_id,
            calories=400,
            protein_g=25,
            carbs_g=40,
            fat_g=15,
            sodium_mg=500,
        ))
        db.add(FoodDataSource(
            food_id=stale_id,
            source_type='QA',
            source_name='QA stale source',
            confidence_level='VERIFIED',
            verified_at=now-timedelta(days=500),
        ))

        missing=FoodItem(
            id=missing_id,
            name_en='Missing QA Meal',
            food_type='RESTAURANT',
            vendor_name='QA Vendor',
            category='QA',
            status='ACTIVE',
        )
        db.add(missing)
        db.add(FoodNutrition(
            food_id=missing_id,
            calories=250,
            protein_g=None,
            carbs_g=None,
            fat_g=None,
            sodium_mg=None,
        ))
        db.commit()

    r=client.get('/api/v1/admin/data-quality',headers=ADMIN_HEADERS,params={'limit':500})
    assert r.status_code==200, r.text
    data=r.json()['data']
    issues={x['food_id']:x for x in data['issues']}

    assert stale_id in issues
    assert issues[stale_id]['source_freshness']=='STALE'
    assert 'SOURCE_STALE' in issues[stale_id]['flags']

    assert missing_id in issues
    assert 'MISSING_SOURCE' in issues[missing_id]['flags']
    assert 'MISSING_CORE_NUTRITION' in issues[missing_id]['flags']
    assert 'MISSING_SODIUM' in issues[missing_id]['flags']

    assert data['summary']['stale'] >= 1
    assert data['summary']['missing_source'] >= 1
    assert data['issue_count'] >= data['returned_issues']


def test_unknown_source_verification_is_visible_not_fresh():
    food_id=f"QA-UNKNOWN-{uuid4().hex[:6]}"
    with SessionLocal() as db:
        food=FoodItem(
            id=food_id,
            name_en='Unknown Verification QA Meal',
            food_type='GROCERY',
            brand_name='QA Brand',
            category='QA',
            status='ACTIVE',
        )
        db.add(food)
        db.add(FoodNutrition(
            food_id=food_id,
            calories=150,
            protein_g=10,
            carbs_g=20,
            fat_g=4,
            sodium_mg=200,
        ))
        db.add(FoodDataSource(
            food_id=food_id,
            source_type='QA',
            source_name='Undated source',
            confidence_level='MEDIUM',
            verified_at=None,
        ))
        db.commit()

    r=client.get(f'/api/v1/foods/{food_id}')
    assert r.status_code==200
    data=r.json()['data']
    assert data['source_freshness']=='UNKNOWN'
    assert data['source_age_days'] is None
