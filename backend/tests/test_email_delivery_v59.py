import os
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.email_delivery import (
    password_reset_delivery_available,
    send_password_reset_email,
)

client=TestClient(app)
PASSWORD='StrongPass123!'


def _register():
    email=f"mail-{uuid4().hex[:10]}@example.com"
    r=client.post('/api/v1/auth/register',json={
        'email':email,'password':PASSWORD,'first_name':'Mail QA'
    })
    assert r.status_code==200
    return email


def _smtp_env():
    return {
        'WAZEN_SMTP_HOST':'smtp.example.test',
        'WAZEN_SMTP_PORT':'587',
        'WAZEN_SMTP_FROM':'no-reply@wazen.test',
        'WAZEN_PASSWORD_RESET_URL_BASE':'https://app.wazen.test/reset-password',
        'WAZEN_SMTP_TLS':'false',
        'WAZEN_SMTP_SSL':'false',
        'WAZEN_SMTP_USERNAME':'smtp-user',
        'WAZEN_SMTP_PASSWORD':'smtp-secret',
    }


def test_delivery_availability_depends_only_on_global_provider_config():
    with patch.dict(os.environ,{
        'WAZEN_SMTP_HOST':'',
        'WAZEN_SMTP_FROM':'',
        'WAZEN_PASSWORD_RESET_URL_BASE':'',
    },clear=False):
        assert password_reset_delivery_available() is False

    with patch.dict(os.environ,_smtp_env(),clear=False):
        assert password_reset_delivery_available() is True


def test_smtp_adapter_sends_reset_link_and_authenticates_without_exposing_password():
    token='abc+/=token'
    with patch.dict(os.environ,_smtp_env(),clear=False):
        with patch('app.services.email_delivery.smtplib.SMTP') as smtp_cls:
            smtp=smtp_cls.return_value.__enter__.return_value
            status=send_password_reset_email('person@example.com',token)

            assert status=='SENT'
            smtp.login.assert_called_once_with('smtp-user','smtp-secret')
            smtp.send_message.assert_called_once()
            msg=smtp.send_message.call_args.args[0]
            body=msg.get_content()
            assert msg['To']=='person@example.com'
            assert msg['From']=='no-reply@wazen.test'
            assert 'https://app.wazen.test/reset-password?token=' in body
            assert 'abc%2B%2F%3Dtoken' in body
            assert 'smtp-secret' not in body


def test_smtp_delivery_failure_is_contained():
    with patch.dict(os.environ,_smtp_env(),clear=False):
        with patch('app.services.email_delivery.smtplib.SMTP',side_effect=OSError('smtp down')):
            assert send_password_reset_email('person@example.com','token')=='FAILED'


def test_forgot_password_public_response_is_identical_for_existing_and_missing_accounts():
    existing=_register()
    missing=f"missing-{uuid4().hex}@example.com"
    env={
        'WAZEN_PASSWORD_RESET_DEBUG':'0',
        'WAZEN_SMTP_HOST':'',
        'WAZEN_SMTP_FROM':'',
        'WAZEN_PASSWORD_RESET_URL_BASE':'',
    }
    with patch.dict(os.environ,env,clear=False):
        existing_r=client.post('/api/v1/auth/forgot-password',json={'email':existing})
        missing_r=client.post('/api/v1/auth/forgot-password',json={'email':missing})

    assert existing_r.status_code==200
    assert missing_r.status_code==200
    existing_data=existing_r.json()['data']
    missing_data=missing_r.json()['data']
    for key in ['accepted','delivery','delivery_available','message']:
        assert existing_data[key]==missing_data[key]
    assert existing_data['delivery']=='GENERIC'
    assert existing_data['delivery_available'] is False
    assert 'debug_reset_token' not in existing_data
    assert 'debug_reset_token' not in missing_data


def test_missing_account_response_stays_generic_even_when_smtp_is_configured():
    missing=f"missing-smtp-{uuid4().hex}@example.com"
    with patch.dict(os.environ,{**_smtp_env(),'WAZEN_PASSWORD_RESET_DEBUG':'0'},clear=False):
        with patch('app.services.email_delivery.smtplib.SMTP') as smtp_cls:
            r=client.post('/api/v1/auth/forgot-password',json={'email':missing})
            assert r.status_code==200
            data=r.json()['data']
            assert data['delivery']=='GENERIC'
            assert data['delivery_available'] is True
            smtp_cls.assert_not_called()
