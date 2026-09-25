import os
from urllib.parse import urlparse

from app.config import RuntimeConfig, DEFAULT_DEV_JWT_SECRET, safe_runtime_summary
from app.services.integration_capabilities import integration_capabilities


def production_launch_gate(config: RuntimeConfig, readiness: dict) -> dict:
    caps=integration_capabilities(config)
    blockers=[]
    warnings=[]
    manual_checks=[]

    def blocker(code: str, area: str, message: str):
        blockers.append({'code':code,'area':area,'message':message})

    def warning(code: str, area: str, message: str):
        warnings.append({'code':code,'area':area,'message':message})

    if config.environment not in {'production','prod'}:
        blocker('ENVIRONMENT_NOT_PRODUCTION','runtime','WAZEN_ENV must be production for the production launch environment.')

    if not readiness.get('ready',False):
        blocker('READINESS_FAILED','runtime','Application readiness checks are not all passing.')

    runtime=safe_runtime_summary(config)
    if runtime['database_backend']!='postgresql':
        blocker('POSTGRESQL_REQUIRED','database','Production must use persistent PostgreSQL.')

    if not config.cors_origins or '*' in config.cors_origins:
        blocker('EXPLICIT_CORS_REQUIRED','security','Production CORS origins must be explicit; wildcard CORS is not allowed.')

    if config.jwt_secret==DEFAULT_DEV_JWT_SECRET or len(config.jwt_secret)<32:
        blocker('STRONG_JWT_SECRET_REQUIRED','security','Production JWT_SECRET must be non-default and at least 32 characters.')

    admin_key=(os.getenv('WAZEN_ADMIN_KEY') or '').strip()
    if len(admin_key)<32:
        blocker('STRONG_ADMIN_KEY_REQUIRED','security','WAZEN_ADMIN_KEY must be configured with at least 32 characters for production admin APIs.')

    if not caps['email_verification']['available']:
        blocker('EMAIL_VERIFICATION_REQUIRED','authentication','Email verification delivery must be configured before production launch.')
    else:
        verify_base=(os.getenv('WAZEN_EMAIL_VERIFY_URL_BASE') or '').strip()
        parsed_verify=urlparse(verify_base)
        if parsed_verify.scheme.lower()!='https' or not parsed_verify.netloc:
            blocker('HTTPS_VERIFY_URL_REQUIRED','authentication','WAZEN_EMAIL_VERIFY_URL_BASE must be an absolute HTTPS URL in production.')

    if not caps['password_reset_email']['available']:
        blocker('PASSWORD_RESET_EMAIL_REQUIRED','authentication','Password reset email delivery must be configured before production launch.')
    else:
        reset_base=(os.getenv('WAZEN_PASSWORD_RESET_URL_BASE') or '').strip()
        parsed=urlparse(reset_base)
        if parsed.scheme.lower()!='https' or not parsed.netloc:
            blocker('HTTPS_RESET_URL_REQUIRED','authentication','WAZEN_PASSWORD_RESET_URL_BASE must be an absolute HTTPS URL in production.')

    if not caps['vision']['available']:
        warning('VISION_NOT_CONFIGURED','vision','Image analysis should remain disabled until a production vision provider/API key is configured.')

    for provider in ('apple','google','mobile_otp'):
        if not caps['auth'][provider]['implemented']:
            warning(
                f'{provider.upper()}_AUTH_NOT_IMPLEMENTED',
                'authentication',
                f'{provider} sign-in is not implemented and must remain disabled in the client.',
            )

    manual_checks.extend([
        {
            'code':'VERIFY_PROVIDER_BACKUPS',
            'area':'database',
            'message':'Confirm managed PostgreSQL backup retention is enabled and record a restore drill against the actual production provider.',
        },
        {
            'code':'VERIFY_REAL_EMAIL_DELIVERY',
            'area':'authentication',
            'message':'Complete real email-verification and password-reset delivery tests against the production/staging mailbox and client URLs.',
        },
        {
            'code':'VERIFY_DOMAIN_TLS',
            'area':'hosting',
            'message':'Verify the final API/app domain, TLS certificate, CORS origins and readiness endpoint from the public network.',
        },
        {
            'code':'VERIFY_NATIVE_SIGNING',
            'area':'mobile',
            'message':'Complete native iOS signing/distribution checks before App Store or Ad Hoc release.',
        },
    ])

    return {
        'status':'READY' if not blockers else 'NOT_READY',
        'ready_for_production':not blockers,
        'blocker_count':len(blockers),
        'warning_count':len(warnings),
        'blockers':blockers,
        'warnings':warnings,
        'manual_checks':manual_checks,
        'runtime':runtime,
        'capabilities':caps,
        'readiness':readiness,
    }
