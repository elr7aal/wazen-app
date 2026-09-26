import pytest

from app.config import RuntimeConfig, validate_runtime_config, safe_runtime_summary


def test_development_allows_local_defaults():
    cfg=RuntimeConfig(
        environment='development',
        database_url='sqlite+pysqlite:///./wazen.db',
        cors_origins=('*',),
        jwt_secret='dev-change-me-please-use-at-least-32-bytes',
    )
    assert validate_runtime_config(cfg)==cfg


@pytest.mark.parametrize('cfg',[
    RuntimeConfig(
        environment='production',
        database_url='postgresql+psycopg://user:pass@db/wazen',
        cors_origins=('https://app.example.com',),
        jwt_secret='dev-change-me-please-use-at-least-32-bytes',
    ),
    RuntimeConfig(
        environment='production',
        database_url='postgresql+psycopg://user:pass@db/wazen',
        cors_origins=('*',),
        jwt_secret='this-is-a-real-production-secret-value-12345',
    ),
    RuntimeConfig(
        environment='production',
        database_url='sqlite+pysqlite:///./wazen.db',
        cors_origins=('https://app.example.com',),
        jwt_secret='this-is-a-real-production-secret-value-12345',
    ),
])
def test_production_rejects_unsafe_runtime_config(cfg):
    with pytest.raises(RuntimeError):
        validate_runtime_config(cfg)


def test_production_accepts_explicit_secure_config():
    cfg=RuntimeConfig(
        environment='production',
        database_url='postgresql+psycopg://user:pass@db/wazen',
        cors_origins=('https://app.example.com','https://admin.example.com'),
        jwt_secret='this-is-a-real-production-secret-value-12345',
    )
    assert validate_runtime_config(cfg)==cfg
    summary=safe_runtime_summary(cfg)
    assert summary=={
        'environment':'production',
        'database_backend':'postgresql',
        'cors_mode':'explicit',
    }
