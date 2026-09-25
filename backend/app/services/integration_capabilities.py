from app.config import RuntimeConfig, safe_runtime_summary
from app.services.email_delivery import password_reset_delivery_available
from app.services.vision import provider_configured as vision_provider_configured


def integration_capabilities(config: RuntimeConfig) -> dict:
    return {
        'auth': {
            'email_password': {
                'implemented': True,
                'available': True,
                'status': 'AVAILABLE',
            },
            'apple': {
                'implemented': False,
                'available': False,
                'status': 'NOT_IMPLEMENTED',
            },
            'google': {
                'implemented': False,
                'available': False,
                'status': 'NOT_IMPLEMENTED',
            },
            'mobile_otp': {
                'implemented': False,
                'available': False,
                'status': 'NOT_IMPLEMENTED',
            },
        },
        'password_reset_email': {
            'implemented': True,
            'available': password_reset_delivery_available(),
            'status': 'AVAILABLE' if password_reset_delivery_available() else 'NOT_CONFIGURED',
        },
        'vision': {
            'implemented': True,
            'available': vision_provider_configured(),
            'status': 'AVAILABLE' if vision_provider_configured() else 'NOT_CONFIGURED',
        },
        'runtime': safe_runtime_summary(config),
    }


def integration_admin_summary(config: RuntimeConfig) -> dict:
    caps=integration_capabilities(config)
    actions=[]
    if not caps['password_reset_email']['available']:
        actions.append({
            'code':'CONFIGURE_PASSWORD_RESET_EMAIL',
            'area':'password_reset_email',
            'message':'Configure SMTP and WAZEN_PASSWORD_RESET_URL_BASE before relying on password recovery in production.',
        })
    if not caps['vision']['available']:
        actions.append({
            'code':'CONFIGURE_VISION_PROVIDER',
            'area':'vision',
            'message':'Configure the production vision provider/API key before enabling image analysis for users.',
        })
    for provider,code in [
        ('apple','IMPLEMENT_APPLE_SIGN_IN'),
        ('google','IMPLEMENT_GOOGLE_SIGN_IN'),
        ('mobile_otp','IMPLEMENT_MOBILE_OTP'),
    ]:
        if not caps['auth'][provider]['implemented']:
            actions.append({
                'code':code,
                'area':provider,
                'message':f'{provider} authentication is not implemented and must remain disabled in the client.',
            })
    if caps['runtime']['database_backend']!='postgresql':
        actions.append({
            'code':'CONFIGURE_PRODUCTION_POSTGRESQL',
            'area':'database',
            'message':'Use persistent PostgreSQL for production.',
        })
    return {
        'capabilities':caps,
        'required_actions':actions,
        'action_count':len(actions),
    }
