from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models.db_models import (
    FoodItem, FoodLog, User, UserProfile, WeeklyPlanItem, WeightHistory
)

MEAL_SPLIT = {
    'BREAKFAST': 0.25,
    'LUNCH': 0.35,
    'DINNER': 0.30,
    'SNACK': 0.10,
}
MEAL_ORDER = ['BREAKFAST', 'LUNCH', 'DINNER', 'SNACK']


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _day_end(d: date) -> datetime:
    return datetime.combine(d + timedelta(days=1), time.min)


def week_start_for(d: date | None = None) -> date:
    d = d or datetime.now(timezone.utc).date()
    return d - timedelta(days=d.weekday())


def _unsafe(food: FoodItem, severe: set[str]) -> bool:
    if not severe:
        return False
    return any(
        a.relationship_type == 'CONTAINS' and a.allergen_code.upper() in severe
        for a in food.allergens
    )


def eligible_foods(db: Session, profile: UserProfile) -> list[FoodItem]:
    severe = {x.upper() for x in profile.severe_allergens()}
    rows = db.scalars(
        select(FoodItem).where(FoodItem.status == 'ACTIVE').order_by(FoodItem.vendor_name, FoodItem.name_en)
    ).all()
    return [
        f for f in rows
        if f.nutrition and f.nutrition.calories is not None and f.nutrition.calories > 0 and not _unsafe(f, severe)
    ]


def _pick_food(pool: list[FoodItem], target: float, offset: int, used: set[str]) -> FoodItem | None:
    candidates = [f for f in pool if f.id not in used] or pool
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda f: (
            abs(float(f.nutrition.calories or 0) - target),
            -(float(f.nutrition.protein_g or 0)),
            f.id,
        )
    )
    window = ranked[: min(8, len(ranked))]
    return window[offset % len(window)]


def generate_week(db: Session, user: User, start: date | None = None, replace: bool = True):
    profile = user.profile
    if not profile:
        raise ValueError('PROFILE_REQUIRED')
    start = start or week_start_for()
    end = start + timedelta(days=7)
    if replace:
        db.execute(delete(WeeklyPlanItem).where(
            WeeklyPlanItem.user_id == user.id,
            WeeklyPlanItem.plan_date >= start,
            WeeklyPlanItem.plan_date < end,
        ))

    pool = eligible_foods(db, profile)
    if not pool:
        raise ValueError('NO_ELIGIBLE_FOODS')

    created = []
    for day_idx in range(7):
        d = start + timedelta(days=day_idx)
        used: set[str] = set()
        for meal_idx, meal in enumerate(MEAL_ORDER):
            target = float(profile.target_calories or 2000) * MEAL_SPLIT[meal]
            food = _pick_food(pool, target, day_idx + meal_idx * 2, used)
            if not food:
                continue
            used.add(food.id)
            n = food.nutrition
            row = WeeklyPlanItem(
                user_id=user.id,
                plan_date=d,
                meal_type=meal,
                food_id=food.id,
                food_name=food.name_ar or food.name_en or food.id,
                calories=float(n.calories or 0),
                protein_g=float(n.protein_g or 0),
                price=food.price,
                currency=food.currency or 'AED',
            )
            db.add(row)
            created.append(row)
    db.commit()
    return serialize_week(db, user.id, start)


def serialize_week(db: Session, user_id: str, start: date):
    end = start + timedelta(days=7)
    rows = db.scalars(select(WeeklyPlanItem).where(
        WeeklyPlanItem.user_id == user_id,
        WeeklyPlanItem.plan_date >= start,
        WeeklyPlanItem.plan_date < end,
    ).order_by(WeeklyPlanItem.plan_date, WeeklyPlanItem.meal_type)).all()
    by_day: dict[date, list[WeeklyPlanItem]] = defaultdict(list)
    for row in rows:
        by_day[row.plan_date].append(row)
    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        items = sorted(by_day.get(d, []), key=lambda x: MEAL_ORDER.index(x.meal_type) if x.meal_type in MEAL_ORDER else 99)
        days.append({
            'date': d.isoformat(),
            'items': [{
                'id': x.id,
                'meal_type': x.meal_type,
                'food_id': x.food_id,
                'food_name': x.food_name,
                'calories': x.calories,
                'protein_g': x.protein_g,
                'price': x.price,
                'currency': x.currency,
                'status': x.status,
            } for x in items],
            'total_calories': sum(x.calories for x in items),
            'total_protein_g': sum(x.protein_g for x in items),
        })
    return {'week_start': start.isoformat(), 'days': days}


def get_or_generate_week(db: Session, user: User, start: date | None = None):
    start = start or week_start_for()
    end = start + timedelta(days=7)
    existing = db.scalar(select(WeeklyPlanItem.id).where(
        WeeklyPlanItem.user_id == user.id,
        WeeklyPlanItem.plan_date >= start,
        WeeklyPlanItem.plan_date < end,
    ).limit(1))
    return serialize_week(db, user.id, start) if existing else generate_week(db, user, start, replace=True)


def rebalance_day(db: Session, user: User, plan_date: date):
    profile = user.profile
    if not profile:
        raise ValueError('PROFILE_REQUIRED')
    db.execute(delete(WeeklyPlanItem).where(
        WeeklyPlanItem.user_id == user.id,
        WeeklyPlanItem.plan_date == plan_date,
    ))
    pool = eligible_foods(db, profile)
    if not pool:
        raise ValueError('NO_ELIGIBLE_FOODS')

    day_offset = (plan_date - week_start_for(plan_date)).days
    used: set[str] = set()
    for meal_idx, meal in enumerate(MEAL_ORDER):
        target = float(profile.target_calories or 2000) * MEAL_SPLIT[meal]
        food = _pick_food(pool, target, day_offset + meal_idx * 3 + 1, used)
        if not food:
            continue
        used.add(food.id)
        db.add(WeeklyPlanItem(
            user_id=user.id,
            plan_date=plan_date,
            meal_type=meal,
            food_id=food.id,
            food_name=food.name_ar or food.name_en or food.id,
            calories=float(food.nutrition.calories or 0),
            protein_g=float(food.nutrition.protein_g or 0),
            price=food.price,
            currency=food.currency or 'AED',
        ))
    db.commit()
    return serialize_week(db, user.id, week_start_for(plan_date))


def record_weight(db: Session, user_id: str, weight_kg: float | None):
    if weight_kg is None:
        return
    latest = db.scalar(select(WeightHistory).where(WeightHistory.user_id == user_id).order_by(WeightHistory.recorded_at.desc()).limit(1))
    if latest and abs(latest.weight_kg - float(weight_kg)) < 0.01:
        return
    db.add(WeightHistory(user_id=user_id, weight_kg=float(weight_kg)))


def progress_summary(db: Session, user: User, days: int):
    days = max(1, min(days, 90))
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)
    start_dt = _day_start(start_date)
    end_dt = _day_end(today)
    logs = db.scalars(select(FoodLog).where(
        FoodLog.user_id == user.id,
        FoodLog.logged_at >= start_dt,
        FoodLog.logged_at < end_dt,
    ).order_by(FoodLog.logged_at)).all()

    profile = user.profile
    target_calories = float(profile.target_calories or 2000) if profile else 2000.0
    target_protein = float(profile.target_protein_g or 0) if profile else 0.0

    grouped = defaultdict(lambda: {'calories': 0.0, 'protein_g': 0.0, 'logs': 0, 'restaurant_spend': 0.0})
    for log in logs:
        d = log.logged_at.date()
        grouped[d]['calories'] += float(log.calories or 0)
        grouped[d]['protein_g'] += float(log.protein_g or 0)
        grouped[d]['logs'] += 1
        if log.food_id:
            food = db.get(FoodItem, log.food_id)
            if food and food.food_type == 'RESTAURANT' and food.price is not None:
                grouped[d]['restaurant_spend'] += float(food.price)

    tracked_days = len(grouped)
    goal_days = sum(
        1 for values in grouped.values()
        if target_calories * 0.85 <= values['calories'] <= target_calories * 1.15
    )
    avg_protein = (
        sum(v['protein_g'] for v in grouped.values()) / tracked_days if tracked_days else 0.0
    )
    avg_calories = (
        sum(v['calories'] for v in grouped.values()) / tracked_days if tracked_days else 0.0
    )
    restaurant_spend = sum(v['restaurant_spend'] for v in grouped.values())

    weights = db.scalars(select(WeightHistory).where(
        WeightHistory.user_id == user.id,
        WeightHistory.recorded_at >= start_dt,
        WeightHistory.recorded_at < end_dt,
    ).order_by(WeightHistory.recorded_at)).all()
    if not weights and profile and profile.weight_kg:
        weights = [WeightHistory(user_id=user.id, weight_kg=float(profile.weight_kg), recorded_at=datetime.now(timezone.utc).replace(tzinfo=None))]

    daily = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        v = grouped.get(d)
        daily.append({
            'date': d.isoformat(),
            'calories': round(v['calories'], 1) if v else 0.0,
            'protein_g': round(v['protein_g'], 1) if v else 0.0,
            'logs': v['logs'] if v else 0,
            'goal_met': bool(v and target_calories * 0.85 <= v['calories'] <= target_calories * 1.15),
        })

    return {
        'range_days': days,
        'start_date': start_date.isoformat(),
        'end_date': today.isoformat(),
        'target_calories': target_calories,
        'target_protein_g': target_protein,
        'tracked_days': tracked_days,
        'goal_days': goal_days,
        'average_calories': round(avg_calories, 1),
        'average_protein_g': round(avg_protein, 1),
        'restaurant_spend_aed': round(restaurant_spend, 2),
        'weight_trend': [{
            'date': x.recorded_at.date().isoformat(),
            'weight_kg': x.weight_kg,
        } for x in weights],
        'daily': daily,
    }
