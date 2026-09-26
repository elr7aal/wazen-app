import json
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client=TestClient(app)


def _admin_headers():
    return {
        'X-WAZEN-ADMIN-KEY':os.environ.get('WAZEN_ADMIN_KEY','test-admin-key'),
        'X-WAZEN-ADMIN-ACTOR':'integration-qa',
    }


def test_public_capabilities_are_safe_and_truthful_by_default():
    env={
        'WAZEN_SMTP_HOST':'',
        'WAZEN_SMTP_FROM':'',
        'WAZEN_PASSWORD_RESET_URL_BASE':'',
        'WAZEN_EMAIL_VERIFY_URL_BASE':'',
        'OPENAI_API_KEY':'',
    }
    with patch.dict(os.environ,env,clear=False):
        r=client.get('/api/v1/capabilities')
    assert r.status_code==200
    data=r.json()['data']
    assert data['auth']['email_password']['available'] is True
    assert data['auth']['apple']['implemented'] is False
    assert data['auth']['google']['implemented'] is False
    assert data['auth']['mobile_otp']['implemented'] is False
    assert data['email_verification']['available'] is False
    assert data['password_reset_email']['available'] is False
    assert data['vision']['available'] is False


def test_capabilities_reflect_configured_email_and_vision_without_leaking_secrets():
    smtp_password='super-secret-smtp-value'
    api_key='super-secret-openai-value'
    env={
        'WAZEN_SMTP_HOST':'smtp.example.test',
        'WAZEN_SMTP_PORT':'587',
        'WAZEN_SMTP_FROM':'no-reply@wazen.test',
        'WAZEN_PASSWORD_RESET_URL_BASE':'https://app.wazen.test/reset-password',
        'WAZEN_EMAIL_VERIFY_URL_BASE':'https://app.wazen.test/verify-email',
        'WAZEN_SMTP_USERNAME':'mailer',
        'WAZEN_SMTP_PASSWORD':smtp_password,
        'OPENAI_API_KEY':api_key,
    }
    with patch.dict(os.environ,env,clear=False):
        r=client.get('/api/v1/capabilities')
        admin=client.get('/api/v1/admin/integrations',headers=_admin_headers())

    assert r.status_code==200
    data=r.json()['data']
    assert data['email_verification']['available'] is True
    assert data['password_reset_email']['available'] is True
    assert data['vision']['available'] is True
    raw=json.dumps(r.json())+json.dumps(admin.json())
    assert smtp_password not in raw
    assert api_key not in raw
    assert 'WAZEN_SMTP_PASSWORD' not in raw
    assert 'OPENAI_API_KEY' not in raw


def test_admin_integration_summary_lists_only_real_remaining_actions():
    env={
        'WAZEN_SMTP_HOST':'',
        'WAZEN_SMTP_FROM':'',
        'WAZEN_PASSWORD_RESET_URL_BASE':'',
        'OPENAI_API_KEY':'',
    }
    with patch.dict(os.environ,env,clear=False):
        r=client.get('/api/v1/admin/integrations',headers=_admin_headers())
    assert r.status_code==200
    data=r.json()['data']
    codes={x['code'] for x in data['required_actions']}
    assert 'CONFIGURE_EMAIL_VERIFICATION' in codes
    assert 'CONFIGURE_PASSWORD_RESET_EMAIL' in codes
    assert 'CONFIGURE_VISION_PROVIDER' in codes
    assert 'IMPLEMENT_APPLE_SIGN_IN' in codes
    assert 'IMPLEMENT_GOOGLE_SIGN_IN' in codes
    assert 'IMPLEMENT_MOBILE_OTP' in codes


def test_admin_integration_summary_requires_admin_key():
    assert client.get('/api/v1/admin/integrations').status_code in (401,503)
