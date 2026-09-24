from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import UserPreferenceSetting


LEVELS={'LOVE','LIKE','NEUTRAL','DISLIKE','NEVER_SHOW'}
TARGET_TYPES={'TERM','FOOD'}


def set_preference(db: Session, user_id: str, target_type: str, target_value: str, level: str):
    target_type=target_type.upper().strip()
    level=level.upper().strip()
    target_value=target_value.strip()
    if target_type not in TARGET_TYPES or level not in LEVELS or not target_value:
        raise ValueError('INVALID_PREFERENCE')
    normalized=target_value.upper() if target_type=='TERM' else target_value
    row=db.scalar(select(UserPreferenceSetting).where(
        UserPreferenceSetting.user_id==user_id,
        UserPreferenceSetting.target_type==target_type,
        UserPreferenceSetting.target_value==normalized,
    ))
    if not row:
        row=UserPreferenceSetting(
            user_id=user_id,
            target_type=target_type,
            target_value=normalized,
            level=level,
        )
        db.add(row)
    else:
        row.level=level
        row.updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(row)
    return serialize_preference(row)


def list_preferences(db: Session, user_id: str):
    rows=db.scalars(select(UserPreferenceSetting).where(
        UserPreferenceSetting.user_id==user_id
    ).order_by(UserPreferenceSetting.target_type,UserPreferenceSetting.target_value)).all()
    return [serialize_preference(x) for x in rows]


def preference_context(db: Session, user_id: str):
    rows=db.scalars(select(UserPreferenceSetting).where(UserPreferenceSetting.user_id==user_id)).all()
    levels={}
    never_terms=[]
    never_foods=[]
    for row in rows:
        if row.level=='NEVER_SHOW':
            if row.target_type=='FOOD':
                never_foods.append(row.target_value)
            else:
                never_terms.append(row.target_value)
        elif row.target_type=='TERM':
            levels[row.target_value]=row.level
    return {
        'preference_levels':levels,
        'never_show_terms':never_terms,
        'never_show_food_ids':never_foods,
    }


def serialize_preference(row: UserPreferenceSetting):
    return {
        'id':row.id,
        'target_type':row.target_type,
        'target_value':row.target_value,
        'level':row.level,
        'updated_at':row.updated_at.isoformat() if row.updated_at else None,
    }
