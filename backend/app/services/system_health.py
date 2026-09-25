from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.config import RuntimeConfig, safe_runtime_summary
from app.models.db_models import FoodItem


def readiness_status(db: Session, config: RuntimeConfig) -> dict:
    checks={
        'database':False,
        'catalog':False,
        'migration_tracking':False,
    }
    errors=[]

    try:
        db.execute(text('SELECT 1'))
        checks['database']=True
    except Exception as exc:
        errors.append(f'database:{type(exc).__name__}')
        return {
            'ready':False,
            'checks':checks,
            'errors':errors,
            **safe_runtime_summary(config),
        }

    try:
        catalog_count=int(db.scalar(select(func.count(FoodItem.id))) or 0)
        checks['catalog']=catalog_count>0
        if catalog_count<=0:
            errors.append('catalog:empty')
    except Exception as exc:
        catalog_count=0
        errors.append(f'catalog:{type(exc).__name__}')

    try:
        inspector=inspect(db.get_bind())
        checks['migration_tracking']='alembic_version' in inspector.get_table_names()
    except Exception:
        checks['migration_tracking']=False

    production=config.environment in {'production','prod'}
    if production and not checks['migration_tracking']:
        errors.append('migrations:not_tracked')

    ready=checks['database'] and checks['catalog'] and (
        checks['migration_tracking'] if production else True
    )
    return {
        'ready':ready,
        'checks':checks,
        'catalog_count':catalog_count,
        'errors':errors,
        **safe_runtime_summary(config),
    }
