import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import RuntimeConfig
from app.main import app
from app.services.launch_readiness import production_launch_gate

client=TestClient(app)


def _production_config():
    return RuntimeConfig(
        environment='production',
        database_url='postgresql+psycopg://user:password@db.example/wazen',
        cors_origins=('https://app.wazen.example','https://admin.wazen.example'),
        jwt_secret='this-is-a-real-production-jwt-secret-value-123456',
    )


def _ready():
    return {
        'ready':True,
        'checks':{'database':True,'catalog':True,'migration_tracking':True},
        'catalog_count':85,
        'errors':[],
        'environment':'production',
        'database_backend':'postgresql',
        'cors_mode':'explicit',
    }


def _provider_env():
    return {
        'WAZEN_ADMIN_KEY':'a-strong-admin-key-with-at-least-32-characters',
        'WAZEN_SMTP_HOST':'smtp.example.test',
        'WAZEN_SMTP_PORT':'587',
        'WAZEN_SMTP_FROM':'no-reply@wazen.example',
        'WAZEN_PASSWORD_RESET_URL_BASE':'https://app.wazen.example/reset-password',
        'WAZEN_EMAIL_VERIFY_URL_BASE':'https://app.wazen.example/verify-email',
        'WAZEN_REQUIRE_EMAIL_VERIFIED':'true',
        'OPENAI_API_KEY':'test-openai-key',
    }


def test_launch_gate_is_ready_when_core_production_requirements_are_met():
    with patch.dict(os.environ,_provider_env(),clear=False):
        data=production_launch_gate(_production_config(),_ready())

    assert data['ready_for_production'] is True
    assert data['status']=='READY'
    assert data['blocker_count']==0
    warning_codes={x['code'] for x in data['warnings']}
    assert 'APPLE_AUTH_NOT_IMPLEMENTED' in warning_codes
    assert 'GOOGLE_AUTH_NOT_IMPLEMENTED' in warning_codes
    assert 'MOBILE_OTP_AUTH_NOT_IMPLEMENTED' in warning_codes


def test_launch_gate_blocks_unsafe_or_incomplete_environment():
    cfg=RuntimeConfig(
        environment='development',
        database_url='sqlite+pysqlite:///./wazen.db',
        cors_origins=('*',),
        jwt_secret='short',
    )
    env={
        'WAZEN_ADMIN_KEY':'short',
        'WAZEN_SMTP_HOST':'',
        'WAZEN_SMTP_FROM':'',
        'WAZEN_PASSWORD_RESET_URL_BASE':'',
        'WAZEN_EMAIL_VERIFY_URL_BASE':'',
        'OPENAI_API_KEY':'',
    }
    readiness={**_ready(),'ready':False,'errors':['database:down']}
    with patch.dict(os.environ,env,clear=False):
        data=production_launch_gate(cfg,readiness)

    codes={x['code'] for x in data['blockers']}
    assert data['ready_for_production'] is False
    assert 'ENVIRONMENT_NOT_PRODUCTION' in codes
    assert 'READINESS_FAILED' in codes
    assert 'POSTGRESQL_REQUIRED' in codes
    assert 'EXPLICIT_CORS_REQUIRED' in codes
    assert 'STRONG_JWT_SECRET_REQUIRED' in codes
    assert 'STRONG_ADMIN_KEY_REQUIRED' in codes
    assert 'EMAIL_VERIFICATION_REQUIRED' in codes
    assert 'PASSWORD_RESET_EMAIL_REQUIRED' in codes


def test_launch_gate_requires_https_password_reset_url():
    env={**_provider_env(),'WAZEN_PASSWORD_RESET_URL_BASE':'http://app.wazen.example/reset-password'}
    with patch.dict(os.environ,env,clear=False):
        data=production_launch_gate(_production_config(),_ready())
    codes={x['code'] for x in data['blockers']}
    assert 'HTTPS_RESET_URL_REQUIRED' in codes


def test_launch_gate_never_exposes_secret_values():
    jwt='jwt-super-secret-value-with-more-than-thirty-two-characters'
    admin='admin-super-secret-value-with-more-than-thirty-two-characters'
    smtp='smtp-super-secret-value'
    openai='openai-super-secret-value'
    cfg=RuntimeConfig(
        environment='production',
        database_url='postgresql+psycopg://secret-user:secret-pass@db/wazen',
        cors_origins=('https://app.wazen.example',),
        jwt_secret=jwt,
    )
    env={
        'WAZEN_ADMIN_KEY':admin,
        'WAZEN_SMTP_HOST':'smtp.example.test',
        'WAZEN_SMTP_PORT':'587',
        'WAZEN_SMTP_FROM':'no-reply@wazen.example',
        'WAZEN_PASSWORD_RESET_URL_BASE':'https://app.wazen.example/reset-password',
        'WAZEN_SMTP_PASSWORD':smtp,
        'OPENAI_API_KEY':openai,
    }
    with patch.dict(os.environ,env,clear=False):
        data=production_launch_gate(cfg,_ready())
    raw=str(data)
    for secret in [jwt,admin,smtp,openai,'secret-pass']:
        assert secret not in raw


def test_admin_launch_readiness_requires_admin_key():
    assert client.get('/api/v1/admin/launch-readiness').status_code in (401,503)


def test_admin_launch_readiness_returns_structured_gate():
    admin_key=os.environ.get('WAZEN_ADMIN_KEY','test-admin-key')
    r=client.get('/api/v1/admin/launch-readiness',headers={
        'X-WAZEN-ADMIN-KEY':admin_key,
        'X-WAZEN-ADMIN-ACTOR':'launch-qa',
    })
    assert r.status_code==200
    data=r.json()['data']
    assert data['status'] in {'READY','NOT_READY'}
    assert isinstance(data['blockers'],list)
    assert isinstance(data['warnings'],list)
    assert isinstance(data['manual_checks'],list)



def test_launch_gate_requires_https_email_verification_url():
    env={**_provider_env(),'WAZEN_EMAIL_VERIFY_URL_BASE':'http://app.wazen.example/verify-email'}
    with patch.dict(os.environ,env,clear=False):
        data=production_launch_gate(_production_config(),_ready())
    codes={x['code'] for x in data['blockers']}
    assert 'HTTPS_VERIFY_URL_REQUIRED' in codes



def test_launch_gate_requires_email_verification_enforcement():
    env={**_provider_env(),'WAZEN_REQUIRE_EMAIL_VERIFIED':'false'}
    with patch.dict(os.environ,env,clear=False):
        data=production_launch_gate(_production_config(),_ready())
    codes={x['code'] for x in data['blockers']}
    assert 'EMAIL_VERIFICATION_ENFORCEMENT_REQUIRED' in codes
