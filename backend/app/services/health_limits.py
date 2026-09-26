from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import HealthLimit

NUTRIENT_ATTRS={
    'CALORIES':'calories',
    'PROTEIN_G':'protein_g',
    'CARBS_G':'carbs_g',
    'FAT_G':'fat_g',
    'SATURATED_FAT_G':'saturated_fat_g',
    'SUGAR_G':'sugar_g',
    'SODIUM_MG':'sodium_mg',
}


def set_health_limit(db: Session, user_id: str, data):
    code=data.nutrient_code.upper()
    row=db.scalar(select(HealthLimit).where(
        HealthLimit.user_id==user_id,
        HealthLimit.nutrient_code==code,
        HealthLimit.limit_type==data.limit_type,
    ))
    if not row:
        row=HealthLimit(
            user_id=user_id,
            nutrient_code=code,
            limit_type=data.limit_type,
            value=data.value,
            unit=data.unit,
            severity=data.severity,
            source_type=data.source_type,
            note=data.note,
            active=data.active,
        )
        db.add(row)
    else:
        row.value=data.value
        row.unit=data.unit
        row.severity=data.severity
        row.source_type=data.source_type
        row.note=data.note
        row.active=data.active
    db.commit()
    db.refresh(row)
    return serialize_health_limit(row)


def list_health_limits(db: Session, user_id: str, active_only: bool=False):
    stmt=select(HealthLimit).where(HealthLimit.user_id==user_id)
    if active_only:
        stmt=stmt.where(HealthLimit.active.is_(True))
    rows=db.scalars(stmt.order_by(HealthLimit.nutrient_code,HealthLimit.limit_type)).all()
    return [serialize_health_limit(x) for x in rows]


def health_limit_rows(db: Session, user_id: str):
    return db.scalars(select(HealthLimit).where(
        HealthLimit.user_id==user_id,
        HealthLimit.active.is_(True),
    )).all()


def evaluate_food_health_limits(food, limits):
    nutrition=food.nutrition
    hard_reasons=[]
    warnings=[]
    if not nutrition:
        if any(x.severity=='HARD' for x in limits):
            hard_reasons.append('MISSING_REQUIRED_HEALTH_DATA')
        elif limits:
            warnings.append('MISSING_HEALTH_DATA')
        return hard_reasons,warnings

    for limit in limits:
        code_value = limit.get('nutrient_code') if isinstance(limit,dict) else limit.nutrient_code
        limit_type = limit.get('limit_type') if isinstance(limit,dict) else limit.limit_type
        threshold = limit.get('value') if isinstance(limit,dict) else limit.value
        severity = limit.get('severity') if isinstance(limit,dict) else limit.severity
        attr=NUTRIENT_ATTRS.get(code_value)
        if not attr:
            continue
        value=getattr(nutrition,attr,None)
        if value is None:
            code=f'MISSING_{code_value}'
            if severity=='HARD':
                hard_reasons.append(code)
            else:
                warnings.append(code)
            continue

        violates=(limit_type=='MAX' and value>threshold) or (limit_type=='MIN' and value<threshold)
        if not violates:
            continue
        code=f'{code_value}_{limit_type}_LIMIT'
        if severity=='HARD':
            hard_reasons.append(code)
        else:
            warnings.append(code)
    return hard_reasons,warnings


def serialize_health_limit(row: HealthLimit):
    return {
        'id':row.id,
        'nutrient_code':row.nutrient_code,
        'limit_type':row.limit_type,
        'value':row.value,
        'unit':row.unit,
        'severity':row.severity,
        'source_type':row.source_type,
        'note':row.note,
        'active':row.active,
        'updated_at':row.updated_at.isoformat() if row.updated_at else None,
    }
