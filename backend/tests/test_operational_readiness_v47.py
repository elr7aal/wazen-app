from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app

client=TestClient(app)


def test_request_id_is_generated_and_echoed():
    r=client.get('/api/v1/health')
    assert r.status_code==200
    request_id=r.headers.get('x-request-id')
    assert request_id
    UUID(request_id)

    custom='qa-request-123'
    r2=client.get('/api/v1/health',headers={'X-Request-ID':custom})
    assert r2.status_code==200
    assert r2.headers.get('x-request-id')==custom


def test_readiness_checks_database_and_catalog():
    r=client.get('/api/v1/readiness')
    assert r.status_code==200,r.text
    data=r.json()['data']
    assert data['ready'] is True
    assert data['checks']['database'] is True
    assert data['checks']['catalog'] is True
    assert data['catalog_count']>0
    assert data['environment']=='development'
