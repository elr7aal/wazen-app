from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.db_models import User, UserProfile, FoodLog, RecommendationFeedback
from app.models.schemas import DailyStateRequest, RecommendationRequest
from app.services.recommendation import recommend_now
from app.services.preferences import preference_context


def ensure_profile(db: Session, user: User) -> UserProfile:
    if user.profile:
        return user.profile
    p = UserProfile(user_id=user.id)
    db.add(p); db.commit(); db.refresh(p)
    return p


def today_totals(db: Session, user_id: str):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.scalars(select(FoodLog).where(FoodLog.user_id == user_id, FoodLog.logged_at >= start)).all()
    return {
        'calories': round(sum(x.calories for x in rows),1),
        'protein_g': round(sum(x.protein_g for x in rows),1),
        'carbs_g': round(sum(x.carbs_g for x in rows),1),
        'fat_g': round(sum(x.fat_g for x in rows),1),
        'sodium_mg': round(sum(x.sodium_mg for x in rows),1),
    }


def build_daily_request(db: Session, user: User) -> DailyStateRequest:
    p = ensure_profile(db, user)
    t = today_totals(db, user.id)
    return DailyStateRequest(
        target_calories=p.target_calories,
        consumed_calories=t['calories'],
        activity_credit=0,
        target_protein_g=p.target_protein_g,
        consumed_protein_g=t['protein_g'],
        target_carbs_g=p.target_carbs_g,
        consumed_carbs_g=t['carbs_g'] if p.target_carbs_g is not None else None,
        target_fat_g=p.target_fat_g,
        consumed_fat_g=t['fat_g'] if p.target_fat_g is not None else None,
        sodium_max_mg=p.sodium_max_mg,
        consumed_sodium_mg=t['sodium_mg'] if p.sodium_max_mg is not None else None,
    )


def behavior_scores(db: Session, user_id: str) -> dict[str,float]:
    scores={}
    logs=db.scalars(select(FoodLog).where(FoodLog.user_id==user_id, FoodLog.food_id.is_not(None))).all()
    for x in logs:
        scores[x.food_id]=scores.get(x.food_id,0.0)+1.5
    feedback=db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.user_id==user_id)).all()
    weights={'SAVE':3.0,'ACCEPT':4.0,'ORDER':5.0,'REJECT':-5.0}
    for f in feedback:
        scores[f.food_id]=scores.get(f.food_id,0.0)+weights.get(f.action,0.0)
    return scores

def recommend_for_user(db: Session, user: User, vendor=None, category=None, max_calories=None, budget_max=None, allow_modifications=True):
    p = ensure_profile(db, user)
    pref_ctx=preference_context(db,user.id)
    req = RecommendationRequest(
        daily_state=build_daily_request(db, user), vendor=vendor, category=category,
        max_calories=max_calories, budget_max=budget_max or p.daily_budget,
        severe_allergens=p.severe_allergens(), allow_modifications=allow_modifications,
        preferred_terms=p.food_preferences(), disliked_terms=p.disliked_foods(), behavior_scores=behavior_scores(db,user.id),
        preference_levels=pref_ctx['preference_levels'],
        food_preference_levels=pref_ctx['food_preference_levels'],
        never_show_terms=pref_ctx['never_show_terms'],
        never_show_food_ids=pref_ctx['never_show_food_ids'],
    )
    return recommend_now(db, req)


def log_catalog_food(db: Session, user: User, food, meal_type: str, quantity: float = 1.0, entry_method: str = 'CATALOG'):
    if not food or not food.nutrition:
        raise ValueError('FOOD_NUTRITION_NOT_AVAILABLE')
    n = food.nutrition
    q = float(quantity)
    row = FoodLog(
        user_id=user.id,
        food_id=food.id,
        food_name=food.name_en or food.name_ar or food.id,
        meal_type=meal_type,
        entry_method=entry_method,
        calories=(n.calories or 0.0) * q,
        protein_g=(n.protein_g or 0.0) * q,
        carbs_g=(n.carbs_g or 0.0) * q,
        fat_g=(n.fat_g or 0.0) * q,
        sodium_mg=(n.sodium_mg or 0.0) * q,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def log_nutrition_snapshot(
    db: Session, user: User, food_id: str | None, food_name: str, meal_type: str,
    calories: float, protein_g: float = 0.0, carbs_g: float = 0.0, fat_g: float = 0.0,
    sodium_mg: float = 0.0, entry_method: str = 'MODIFIED_RECOMMENDATION'
):
    row = FoodLog(
        user_id=user.id, food_id=food_id, food_name=food_name, meal_type=meal_type,
        entry_method=entry_method, calories=calories, protein_g=protein_g,
        carbs_g=carbs_g, fat_g=fat_g, sodium_mg=sodium_mg,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
