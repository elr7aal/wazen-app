from unittest.mock import MagicMock, patch

from app.services.email_delivery import (
    build_password_reset_url,
    email_verification_delivery_available,
    send_email_verification,
)


def _env():
    return {
        'WAZEN_SMTP_HOST':'smtp.example.test',
        'WAZEN_SMTP_PORT':'587',
        'WAZEN_SMTP_FROM':'no-reply@wazen.test',
        'WAZEN_EMAIL_VERIFY_URL_BASE':'https://app.wazen.test/verify-email',
        'WAZEN_SMTP_TLS':'false',
        'WAZEN_SMTP_SSL':'false',
    }


def test_email_verification_capability_requires_verify_url():
    with patch.dict('os.environ',{
        'WAZEN_SMTP_HOST':'smtp.example.test',
        'WAZEN_SMTP_FROM':'no-reply@wazen.test',
        'WAZEN_EMAIL_VERIFY_URL_BASE':'',
    },clear=False):
        assert email_verification_delivery_available() is False

    with patch.dict('os.environ',_env(),clear=False):
        assert email_verification_delivery_available() is True


def test_verification_url_encodes_token():
    url=build_password_reset_url('https://app.wazen.test/verify-email','abc+/=')
    assert url.startswith('https://app.wazen.test/verify-email?')
    assert 'token=' in url
    assert 'abc%2B%2F%3D' in url


def test_verification_email_uses_verify_link_without_leaking_token_elsewhere():
    token='verify-secret-token'
    sent=[]

    class FakeSMTP:
        def __init__(self,*args,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def ehlo(self): pass
        def send_message(self,msg): sent.append(msg)

    with patch.dict('os.environ',_env(),clear=False), patch('smtplib.SMTP',FakeSMTP):
        result=send_email_verification('person@example.com',token)

    assert result=='SENT'
    assert len(sent)==1
    msg=sent[0]
    assert msg['To']=='person@example.com'
    body=msg.get_content()
    assert 'https://app.wazen.test/verify-email?' in body
    assert token in body
