import os
from dataclasses import dataclass


DEFAULT_DEV_JWT_SECRET='dev-change-me-please-use-at-least-32-bytes'


@dataclass(frozen=True)
class RuntimeConfig:
    environment: str
    database_url: str
    cors_origins: tuple[str, ...]
    jwt_secret: str


def read_runtime_config() -> RuntimeConfig:
    environment=os.getenv('WAZEN_ENV','development').strip().lower()
    database_url=os.getenv('DATABASE_URL','sqlite+pysqlite:///./wazen.db').strip()
    cors_raw=os.getenv('WAZEN_CORS_ORIGINS','*')
    cors_origins=tuple(x.strip() for x in cors_raw.split(',') if x.strip())
    jwt_secret=os.getenv('JWT_SECRET',DEFAULT_DEV_JWT_SECRET)
    return RuntimeConfig(
        environment=environment,
        database_url=database_url,
        cors_origins=cors_origins,
        jwt_secret=jwt_secret,
    )


def validate_runtime_config(config: RuntimeConfig | None=None) -> RuntimeConfig:
    config=config or read_runtime_config()
    if config.environment not in {'production','prod'}:
        return config

    errors=[]
    if config.jwt_secret==DEFAULT_DEV_JWT_SECRET or len(config.jwt_secret)<32:
        errors.append('JWT_SECRET must be a non-default secret with at least 32 characters')
    if not config.cors_origins or '*' in config.cors_origins:
        errors.append('WAZEN_CORS_ORIGINS must explicitly list allowed origins in production')
    if config.database_url.startswith('sqlite'):
        errors.append('Production DATABASE_URL must use a persistent database, not SQLite')

    if errors:
        raise RuntimeError('Unsafe production configuration: '+'; '.join(errors))
    return config


def safe_runtime_summary(config: RuntimeConfig | None=None) -> dict:
    config=config or read_runtime_config()
    if config.database_url.startswith('postgresql'):
        database_backend='postgresql'
    elif config.database_url.startswith('sqlite'):
        database_backend='sqlite'
    else:
        database_backend='other'
    return {
        'environment':config.environment,
        'database_backend':database_backend,
        'cors_mode':'wildcard' if '*' in config.cors_origins else 'explicit',
    }
