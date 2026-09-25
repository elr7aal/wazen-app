import os
os.environ['WAZEN_ADMIN_KEY'] = 'test-admin-key'

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
HEADERS = {
    'X-WAZEN-ADMIN-KEY': 'test-admin-key',
    'X-WAZEN-ADMIN-ACTOR': 'qa-admin',
}


def test_admin_requires_key():
    r = client.get('/api/v1/admin/foods')
    assert r.status_code == 401


def test_import_dry_run_does_not_write():
    payload = {
        'format': 'JSON',
        'dry_run': True,
        'records': [{
            'id': 'QA-IMPORT-001',
            'name_en': 'QA Chicken Bowl',
            'food_type': 'RESTAURANT',
            'vendor_name': 'QA Kitchen',
            'serving_size': 1,
            'serving_unit': 'meal',
            'calories': 510,
            'protein_g': 34,
            'carbs_g': 55,
            'fat_g': 16,
            'sodium_mg': 740,
        }],
    }
    r = client.post('/api/v1/admin/import/foods', json=payload, headers=HEADERS)
    assert r.status_code == 200
    data = r.json()['data']
    assert data['summary']['dry_run'] is True
    assert data['summary']['errors'] == 0
    assert data['rows'][0]['operation'] == 'CREATE'
    assert client.get('/api/v1/foods/QA-IMPORT-001').status_code == 404


def test_import_commit_review_and_audit():
    payload = {
        'format': 'JSON',
        'dry_run': False,
        'records': [{
            'id': 'QA-IMPORT-002',
            'name_en': 'QA Protein Bowl',
            'name_ar': 'وعاء بروتين تجريبي',
            'food_type': 'RESTAURANT',
            'vendor_name': 'QA Kitchen',
            'category': 'BOWLS',
            'calories': 430,
            'protein_g': 42,
            'carbs_g': 38,
            'fat_g': 12,
            'sodium_mg': 610,
        }],
    }
    r = client.post('/api/v1/admin/import/foods', json=payload, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()['data']['summary']['created'] == 1

    detail = client.get('/api/v1/foods/QA-IMPORT-002')
    assert detail.status_code == 200
    assert detail.json()['data']['nutrition']['calories'] == 430

    review = client.post(
        '/api/v1/admin/foods/QA-IMPORT-002/review',
        json={'action': 'APPROVE', 'note': 'Verified in QA'},
        headers=HEADERS,
    )
    assert review.status_code == 200
    assert review.json()['data']['review_status'] == 'APPROVE'

    listing = client.get('/api/v1/admin/foods', params={'q': 'QA Protein'}, headers=HEADERS)
    assert listing.status_code == 200
    item = listing.json()['data']['items'][0]
    assert item['review']['review_status'] == 'APPROVE'

    audit = client.get('/api/v1/admin/audit', headers=HEADERS)
    assert audit.status_code == 200
    actions = [x['action'] for x in audit.json()['data']['items']]
    assert 'FOOD_IMPORT' in actions
    assert 'FOOD_APPROVE' in actions


def test_import_validation_duplicate_barcode_and_negative_calories():
    payload = {
        'format': 'JSON',
        'dry_run': True,
        'records': [
            {'id': 'QA-BAD-1', 'name_en': 'Bad One', 'barcode': 'QA-DUP-1', 'calories': -10},
            {'id': 'QA-BAD-2', 'name_en': 'Bad Two', 'barcode': 'QA-DUP-1', 'calories': 100},
        ],
    }
    r = client.post('/api/v1/admin/import/foods', json=payload, headers=HEADERS)
    assert r.status_code == 200
    rows = r.json()['data']['rows']
    assert any('calories: must be >= 0' in x for x in rows[0]['errors'])
    assert any('barcode: duplicate in payload' in x for x in rows[1]['errors'])


def test_csv_dry_run_supported():
    csv_text = 'id,name_en,food_type,calories,protein_g\nQA-CSV-1,CSV Bowl,RESTAURANT,390,30\n'
    r = client.post('/api/v1/admin/import/foods', json={
        'format': 'CSV',
        'dry_run': True,
        'csv_text': csv_text,
    }, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()['data']['summary']['total'] == 1
    assert r.json()['data']['summary']['errors'] == 0


def test_admin_edit_records_before_after_audit():
    payload = {
        'format': 'JSON',
        'dry_run': False,
        'records': [{
            'id': 'QA-EDIT-001',
            'name_en': 'Editable Meal',
            'food_type': 'RESTAURANT',
            'vendor_name': 'QA Kitchen',
            'calories': 500,
            'protein_g': 25,
            'carbs_g': 50,
            'fat_g': 18,
            'sodium_mg': 900,
        }],
    }
    create=client.post('/api/v1/admin/import/foods',json=payload,headers=HEADERS)
    assert create.status_code==200

    edit=client.patch('/api/v1/admin/foods/QA-EDIT-001',headers=HEADERS,json={
        'changes':{
            'name_ar':'وجبة معدلة',
            'nutrition':{
                'calories':460,
                'protein_g':31,
                'sodium_mg':700,
            },
            'allergens':[
                {'code':'MILK','relationship_type':'CONTAINS'},
                {'code':'SESAME','relationship_type':'MAY_CONTAIN'},
            ],
        }
    })
    assert edit.status_code==200,edit.text
    data=edit.json()['data']
    assert data['name_ar']=='وجبة معدلة'
    assert data['nutrition']['calories']==460
    assert {x['code'] for x in data['allergens']}=={'MILK','SESAME'}

    audit=client.get('/api/v1/admin/audit',headers=HEADERS)
    assert audit.status_code==200
    rows=audit.json()['data']['items']
    row=next(x for x in rows if x['action']=='FOOD_EDIT' and x['entity_id']=='QA-EDIT-001')
    import json as _json
    details=_json.loads(row['details_json'])
    assert details['before']['nutrition']['calories']==500
    assert details['after']['nutrition']['calories']==460


def test_admin_merge_moves_references_and_soft_retires_source():
    source_payload = {
        'format':'JSON','dry_run':False,
        'records':[
            {
                'id':'QA-MERGE-SOURCE',
                'name_en':'Duplicate Meal',
                'food_type':'RESTAURANT',
                'vendor_name':'QA Kitchen',
                'calories':410,
                'protein_g':22,
                'carbs_g':44,
                'fat_g':14,
                'sodium_mg':620,
            },
            {
                'id':'QA-MERGE-TARGET',
                'name_en':'Canonical Meal',
                'food_type':'RESTAURANT',
                'vendor_name':'QA Kitchen',
                'calories':410,
                'protein_g':22,
                'carbs_g':44,
                'fat_g':14,
                'sodium_mg':620,
            },
        ],
    }
    r=client.post('/api/v1/admin/import/foods',json=source_payload,headers=HEADERS)
    assert r.status_code==200

    auth=client.post('/api/v1/auth/register',json={
        'email':'merge-admin-test@example.com',
        'password':'StrongPass123!',
        'first_name':'Merge QA',
    })
    assert auth.status_code in (200,409)
    if auth.status_code==200:
        token=auth.json()['data']['access_token']
    else:
        login=client.post('/api/v1/auth/login',json={
            'email':'merge-admin-test@example.com',
            'password':'StrongPass123!',
        })
        token=login.json()['data']['access_token']
    user_headers={'Authorization':f'Bearer {token}'}

    log=client.post('/api/v1/food-log/from-catalog',headers=user_headers,json={
        'food_id':'QA-MERGE-SOURCE',
        'meal_type':'LUNCH',
        'quantity':1,
    })
    assert log.status_code==200
    log_id=log.json()['data']['log']['id']
    fav=client.post(f'/api/v1/food-log/{log_id}/favorite',headers=user_headers)
    assert fav.status_code==200

    merge=client.post('/api/v1/admin/foods/merge',headers=HEADERS,json={
        'source_id':'QA-MERGE-SOURCE',
        'target_id':'QA-MERGE-TARGET',
    })
    assert merge.status_code==200,merge.text
    assert merge.json()['data']['source_status']=='MERGED'

    day=client.get('/api/v1/food-log/today',headers=user_headers).json()['data']['items']
    assert any(x['id']==log_id and x['food_id']=='QA-MERGE-TARGET' for x in day)

    favorites=client.get('/api/v1/food-log/favorites',headers=user_headers).json()['data']['items']
    assert any(x['food_id']=='QA-MERGE-TARGET' for x in favorites)

    search=client.get('/api/v1/foods/search',params={'q':'Duplicate Meal'})
    assert search.status_code==200
    assert all(x['food_id']!='QA-MERGE-SOURCE' for x in search.json()['data']['items'])

    audit=client.get('/api/v1/admin/audit',headers=HEADERS).json()['data']['items']
    assert any(x['action']=='FOOD_MERGE' and x['entity_id']=='QA-MERGE-TARGET' for x in audit)
