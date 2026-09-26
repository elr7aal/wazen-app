import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode


class PasswordResetEmailConfig:
    def __init__(self):
        self.host=(os.getenv('WAZEN_SMTP_HOST') or '').strip()
        self.port=int(os.getenv('WAZEN_SMTP_PORT','587'))
        self.username=(os.getenv('WAZEN_SMTP_USERNAME') or '').strip()
        self.password=os.getenv('WAZEN_SMTP_PASSWORD') or ''
        self.from_address=(os.getenv('WAZEN_SMTP_FROM') or '').strip()
        self.reset_url_base=(os.getenv('WAZEN_PASSWORD_RESET_URL_BASE') or '').strip()
        self.use_tls=(os.getenv('WAZEN_SMTP_TLS','true').strip().lower() in {'1','true','yes','on'})
        self.use_ssl=(os.getenv('WAZEN_SMTP_SSL','false').strip().lower() in {'1','true','yes','on'})
        self.timeout=float(os.getenv('WAZEN_SMTP_TIMEOUT_SECONDS','10'))

    @property
    def configured(self) -> bool:
        return bool(self.host and self.port and self.from_address and self.reset_url_base)


def password_reset_delivery_available() -> bool:
    return PasswordResetEmailConfig().configured


def build_password_reset_url(base: str, token: str) -> str:
    separator='&' if '?' in base else '?'
    return f"{base}{separator}{urlencode({'token':token})}"


def send_password_reset_email(to_email: str, token: str) -> str:
    cfg=PasswordResetEmailConfig()
    if not cfg.configured:
        return 'NOT_CONFIGURED'

    reset_url=build_password_reset_url(cfg.reset_url_base,token)
    msg=EmailMessage()
    msg['Subject']='WAZEN password reset'
    msg['From']=cfg.from_address
    msg['To']=to_email
    msg.set_content(
        'You requested a password reset for your WAZEN account.\n\n'
        f'Open this link to continue:\n{reset_url}\n\n'
        'If you did not request this change, you can ignore this message.\n'
        'This link is time-limited and can be used only once.'
    )

    try:
        if cfg.use_ssl:
            context=ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg.host,cfg.port,timeout=cfg.timeout,context=context) as smtp:
                if cfg.username:
                    smtp.login(cfg.username,cfg.password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg.host,cfg.port,timeout=cfg.timeout) as smtp:
                smtp.ehlo()
                if cfg.use_tls:
                    context=ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if cfg.username:
                    smtp.login(cfg.username,cfg.password)
                smtp.send_message(msg)
        return 'SENT'
    except Exception:
        return 'FAILED'


class EmailVerificationConfig(PasswordResetEmailConfig):
    def __init__(self):
        super().__init__()
        self.verify_url_base=(os.getenv('WAZEN_EMAIL_VERIFY_URL_BASE') or '').strip()

    @property
    def configured(self) -> bool:
        return bool(self.host and self.port and self.from_address and self.verify_url_base)


def email_verification_delivery_available() -> bool:
    return EmailVerificationConfig().configured


def send_email_verification(to_email: str, token: str) -> str:
    cfg=EmailVerificationConfig()
    if not cfg.configured:
        return 'NOT_CONFIGURED'

    verify_url=build_password_reset_url(cfg.verify_url_base,token)
    msg=EmailMessage()
    msg['Subject']='Verify your WAZEN email'
    msg['From']=cfg.from_address
    msg['To']=to_email
    msg.set_content(
        'Verify the email address for your WAZEN account.\n\n'
        f'Open this link to continue:\n{verify_url}\n\n'
        'If you did not create this account, you can ignore this message.\n'
        'This link is time-limited and can be used only once.'
    )

    try:
        if cfg.use_ssl:
            context=ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg.host,cfg.port,timeout=cfg.timeout,context=context) as smtp:
                if cfg.username:
                    smtp.login(cfg.username,cfg.password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg.host,cfg.port,timeout=cfg.timeout) as smtp:
                smtp.ehlo()
                if cfg.use_tls:
                    context=ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if cfg.username:
                    smtp.login(cfg.username,cfg.password)
                smtp.send_message(msg)
        return 'SENT'
    except Exception:
        return 'FAILED'
