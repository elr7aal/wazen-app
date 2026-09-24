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
