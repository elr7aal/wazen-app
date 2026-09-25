from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.db_models import FoodAllergen, FoodDataSource, FoodItem, FoodNutrition

client=TestClient(app)


def _headers():
    email=f"source-rank-{uuid4().hex[:8]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':'StrongPass123!','first_name':'Source Rank QA'
    })
    assert r.status_code==200
    return {'Authorization':f"Bearer {r.json()['data']['access_token']}"}


def _add_food(food_id,verified_at,allergen=None):
    with SessionLocal() as db:
        db.add(FoodItem(
            id=food_id,
            name_en=food_id,
            food_type='RESTAURANT',
            vendor_name='QA Source Vendor',
            category='QA_SOURCE',
            status='ACTIVE',
            availability_status='AVAILABLE',
            price=25,
            currency='AED',
        ))
        db.add(FoodNutrition(
            food_id=food_id,
            calories=420,
            protein_g=30,
            carbs_g=42,
            fat_g=14,
            sodium_mg=520,
        ))
        db.add(FoodDataSource(
            food_id=food_id,
            source_type='QA',
            source_name='QA verified source',
            confidence_level='VERIFIED',
            verified_at=verified_at,
        ))
        if allergen:
            db.add(FoodAllergen(
                food_id=food_id,
                allergen_code=allergen,
                relationship_type='CONTAINS',
            ))
        db.commit()


def test_fresh_source_gets_small_bounded_ranking_advantage():
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    fresh_id=f"QA-FRESH-{uuid4().hex[:6]}"
    stale_id=f"QA-STALE-{uuid4().hex[:6]}"
    _add_food(fresh_id,now-timedelta(days=10))
    _add_food(stale_id,now-timedelta(days=500))

    h=_headers()
    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'QA Source Vendor',
        'category':'QA_SOURCE',
    })
    assert r.status_code==200, r.text
    by_id={x['food_id']:x for x in r.json()['data']['results']}
    fresh=by_id[fresh_id]
    stale=by_id[stale_id]

    assert fresh['scores']['source_quality']==100
    assert stale['scores']['source_quality']==75
    assert fresh['scores']['wazen'] > stale['scores']['wazen']
    assert fresh['scores']['wazen']-stale['scores']['wazen'] <= 2
    assert fresh['source_freshness']=='FRESH'
    assert stale['source_freshness']=='STALE'
    assert 'SOURCE_STALE' in stale['warnings']


def test_source_quality_never_overrides_severe_allergy_exclusion():
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    allergic_id=f"QA-ALLERGY-{uuid4().hex[:6]}"
    safe_id=f"QA-SAFE-{uuid4().hex[:6]}"
    _add_food(allergic_id,now,allergen='MILK')
    _add_food(safe_id,now-timedelta(days=500))

    h=_headers()
    update=client.patch('/api/v1/users/me',headers=h,json={
        'severe_allergens':['MILK']
    })
    assert update.status_code==200

    r=client.post('/api/v1/recommendations/for-me',headers=h,json={
        'vendor':'QA Source Vendor',
        'category':'QA_SOURCE',
    })
    assert r.status_code==200
    data=r.json()['data']
    assert all(x['food_id']!=allergic_id for x in data['results'])
    assert any(
        x['food_id']==allergic_id and x['reason']=='SEVERE_ALLERGY'
        for x in data['excluded']
    )
