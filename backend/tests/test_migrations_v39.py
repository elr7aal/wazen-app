import os
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


BACKEND_DIR=Path(__file__).resolve().parents[1]


def _upgrade(url: str):
    cfg=Config(str(BACKEND_DIR/'alembic.ini'))
    cfg.set_main_option('sqlalchemy.url',url)
    previous=os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL']=url
    try:
        command.upgrade(cfg,'head')
    finally:
        if previous is None:
            os.environ.pop('DATABASE_URL',None)
        else:
            os.environ['DATABASE_URL']=previous


def test_alembic_baseline_creates_current_schema_and_is_idempotent(tmp_path):
    db_path=tmp_path/'migration-test.db'
    url=f"sqlite+pysqlite:///{db_path}"

    _upgrade(url)
    _upgrade(url)

    engine=sa.create_engine(url)
    inspector=sa.inspect(engine)
    tables=set(inspector.get_table_names())

    assert 'users' in tables
    assert 'user_profiles' in tables
    assert 'food_items' in tables
    assert 'auth_sessions' in tables
    assert 'health_limits' in tables
    assert 'recommendation_exclusion_logs' in tables
    assert 'recommendation_decision_logs' in tables
    assert 'idempotency_records' in tables
    assert 'auth_rate_limits' in tables
    assert 'security_events' in tables

    profile_cols={x['name'] for x in inspector.get_columns('user_profiles')}
    log_cols={x['name'] for x in inspector.get_columns('food_logs')}
    favorite_cols={x['name'] for x in inspector.get_columns('favorite_meals')}

    assert 'target_fiber_g' in profile_cols
    assert 'condition_context_csv' in profile_cols
    assert 'fiber_g' in log_cols
    assert 'fiber_g' in favorite_cols
