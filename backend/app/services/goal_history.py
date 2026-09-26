import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import GoalHistory, UserProfile


TRACKED_FIELDS = (
    'weight_kg',
    'target_weight_kg',
    'activity_level',
    'goal_type',
    'daily_budget',
    'target_calories',
    'target_protein_g',
    'target_carbs_g',
    'target_fat_g',
    'target_fiber_g',
    'sodium_max_mg',
)


def snapshot_profile(profile: UserProfile) -> dict:
    return {field:getattr(profile, field) for field in TRACKED_FIELDS}


def add_goal_snapshot(db: Session, user_id: str, profile: UserProfile, reason: str):
    snapshot=snapshot_profile(profile)
    latest=db.scalar(
        select(GoalHistory)
        .where(GoalHistory.user_id==user_id)
        .order_by(GoalHistory.created_at.desc())
        .limit(1)
    )
    if latest:
        try:
            if json.loads(latest.snapshot_json)==snapshot:
                return latest, False
        except Exception:
            pass
    row=GoalHistory(
        user_id=user_id,
        reason=reason,
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, default=str),
    )
    db.add(row)
    return row, True


def serialize_goal_history(row: GoalHistory) -> dict:
    try:
        snapshot=json.loads(row.snapshot_json)
    except Exception:
        snapshot={}
    return {
        'id':row.id,
        'reason':row.reason,
        'snapshot':snapshot,
        'created_at':row.created_at.isoformat(),
    }


def list_goal_history(db: Session, user_id: str, limit: int=50):
    rows=db.scalars(
        select(GoalHistory)
        .where(GoalHistory.user_id==user_id)
        .order_by(GoalHistory.created_at.desc())
        .limit(max(1,min(limit,200)))
    ).all()
    return [serialize_goal_history(x) for x in rows]
