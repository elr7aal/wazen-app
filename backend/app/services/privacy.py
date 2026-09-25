from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.db_models import (
    User, UserProfile, FoodLog, RecommendationFeedback, WeeklyPlanItem,
    WeightHistory, AuthSession, PasswordResetToken, GoalHistory,
    UserPreferenceSetting, HealthLimit, FavoriteMeal, ActivityLog,
    RecommendationExclusionLog, RecommendationDecisionLog, IdempotencyRecord,
)


EXPORT_MODELS = (
    ('food_logs', FoodLog),
    ('recommendation_feedback', RecommendationFeedback),
    ('weekly_plan', WeeklyPlanItem),
    ('weight_history', WeightHistory),
    ('goal_history', GoalHistory),
    ('preferences', UserPreferenceSetting),
    ('health_limits', HealthLimit),
    ('favorite_meals', FavoriteMeal),
    ('activity_logs', ActivityLog),
    ('recommendation_exclusions', RecommendationExclusionLog),
    ('recommendation_decisions', RecommendationDecisionLog),
)

DELETE_MODELS = (
    IdempotencyRecord,
    RecommendationDecisionLog,
    RecommendationExclusionLog,
    ActivityLog,
    FavoriteMeal,
    HealthLimit,
    UserPreferenceSetting,
    GoalHistory,
    PasswordResetToken,
    AuthSession,
    WeightHistory,
    WeeklyPlanItem,
    RecommendationFeedback,
    FoodLog,
    UserProfile,
)

SENSITIVE_FIELDS = {
    'password_hash',
    'refresh_token_hash',
    'token_hash',
    'request_hash',
    'response_json',
}


def _value(value: Any):
    if isinstance(value,(datetime,date)):
        return value.isoformat()
    return value


def serialize_row(row,exclude: set[str] | None=None):
    exclude=(exclude or set())|SENSITIVE_FIELDS
    return {
        col.name:_value(getattr(row,col.name))
        for col in row.__table__.columns
        if col.name not in exclude
    }


def export_user_data(db: Session,user: User):
    profile=db.scalar(select(UserProfile).where(UserProfile.user_id==user.id))
    data={
        'export_version':'1',
        'account':serialize_row(user,{'password_hash'}),
        'profile':serialize_row(profile) if profile else None,
    }
    for key,model in EXPORT_MODELS:
        rows=db.scalars(select(model).where(model.user_id==user.id)).all()
        data[key]=[serialize_row(x) for x in rows]

    # Security credentials, token hashes and idempotency payload caches are
    # intentionally excluded from the portable export.
    data['security']={
        'active_sessions_count':len(db.scalars(select(AuthSession).where(
            AuthSession.user_id==user.id,
            AuthSession.revoked_at.is_(None),
        )).all()),
        'credentials_exported':False,
    }
    return data


def delete_user_data(db: Session,user_id: str):
    counts={}
    for model in DELETE_MODELS:
        result=db.execute(delete(model).where(model.user_id==user_id))
        counts[model.__tablename__]=int(result.rowcount or 0)
    result=db.execute(delete(User).where(User.id==user_id))
    counts['users']=int(result.rowcount or 0)
    db.commit()
    return counts
