import re
import os
import secrets
from uuid import uuid4
from typing import Optional, Any, Literal
from datetime import date
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db, SessionLocal
from app.models.db_models import User, UserProfile, FoodLog, FoodItem, FoodModifier, RecommendationFeedback, AdminAuditLog, FavoriteMeal, ActivityLog
from app.models.schemas import (
    DailyStateRequest, RecommendationRequest, MakeItFitRequest, RebalanceRequest,
    RegisterRequest, LoginRequest, ProfileUpdateRequest, FoodLogCreateRequest,
    UserRecommendationRequest, CatalogFoodLogRequest, GoldenFlowRequest, ModifiedCatalogFoodLogRequest, FoodLogUpdateRequest, OnboardingCompleteRequest, TextFoodParseRequest, ImageFoodAnalyzeRequest, RecommendationFeedbackRequest, PlanRecalculateRequest,
    RefreshTokenRequest, LogoutRequest, ForgotPasswordRequest, ResetPasswordRequest,
    PreferenceSettingRequest, HealthLimitRequest, ActivityLogCreateRequest,
)
from app.security import hash_password, verify_password, create_access_token
from app.deps import get_current_user
from app.services.daily_state import calculate_daily_state
from app.services.recommendation import recommend_now
from app.services.make_it_fit import make_it_fit
from app.services.rebalance import rebalance_day
from app.services.persistence import ensure_profile, build_daily_request, today_totals, today_activity_credit, recommend_for_user, log_catalog_food, log_nutrition_snapshot
from app.services.catalog import ensure_catalog_seeded, query_foods, serialize_food
from app.services.vision import analyze_food_image
from app.services.onboarding import calculate_targets
from app.services.profile_insights import profile_insights
from app.services.admin_data import list_admin_foods, set_review, parse_import_payload, import_foods, edit_food, merge_foods
from app.services.plan_progress import get_or_generate_week, generate_week, rebalance_day as rebalance_plan_day, progress_summary, record_weight, week_start_for
from app.services.auth_sessions import issue_session, rotate_session, revoke_session, revoke_all_sessions, create_password_reset, consume_password_reset, list_active_sessions
from app.services.goal_history import add_goal_snapshot, list_goal_history
from app.services.preferences import set_preference, list_preferences
from app.services.health_limits import set_health_limit, list_health_limits
from app.services.natural_language import parse_natural_food_text
from app.services.recommendation_audit import list_exclusions, list_decisions
from app.config import validate_runtime_config, safe_runtime_summary
from app.services.system_health import readiness_status
from app.services.vision_review import build_vision_review
from app.services.craving_parser import parse_craving_text
from app.services.idempotency import begin_idempotent, finish_idempotent, abandon_idempotent

_runtime_config = validate_runtime_config()
Base.metadata.create_all(bind=engine)

with SessionLocal() as _seed_db:
    ensure_catalog_seeded(_seed_db)

app = FastAPI(title='WAZEN API', version='1.9.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_runtime_config.cors_origins),
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def request_id_middleware(request: Request, call_next):
    request_id=request.headers.get('X-Request-ID') or str(uuid4())
    response=await call_next(request)
    response.headers['X-Request-ID']=request_id
    return response



def _begin_write_idempotency(db: Session, user: User, key: Optional[str], path: str, payload: Any):
    try:
        result=begin_idempotent(
            db,
            user_id=user.id,
            method='POST',
            path=path,
            key=key,
            payload=payload,
        )
    except ValueError as exc:
        code=str(exc)
        if code=='INVALID_IDEMPOTENCY_KEY':
            raise HTTPException(status_code=422,detail='Invalid Idempotency-Key')
        if code=='IDEMPOTENCY_PAYLOAD_CONFLICT':
            raise HTTPException(status_code=409,detail='Idempotency-Key was already used with a different request')
        raise HTTPException(status_code=409,detail='A request with this Idempotency-Key is already in progress')
    return result


def envelope(data=None, error=None, meta=None):
    return {'success': error is None, 'data': data, 'error': error, 'meta': meta or {}}


@app.get('/api/v1/health')
def health():
    return envelope({'status': 'ok', 'service': 'wazen-api', 'version': '1.9.0', **safe_runtime_summary(_runtime_config)})


@app.get('/api/v1/readiness')
def readiness(response: Response, db: Session = Depends(get_db)):
    data=readiness_status(db,_runtime_config)
    if not data['ready']:
        response.status_code=503
    return envelope(data)


# -------- Authentication --------
@app.post('/api/v1/auth/register')
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    if '@' not in email:
        raise HTTPException(status_code=422, detail='Valid email required')
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail='Email already registered')
    u = User(email=email, password_hash=hash_password(req.password), first_name=req.first_name, language=req.language)
    db.add(u); db.flush()
    p = UserProfile(user_id=u.id)
    db.add(p); db.commit(); db.refresh(u)
    session = issue_session(db, u.id)
    return envelope({'user_id': u.id, **session})


@app.post('/api/v1/auth/login')
def login(req: LoginRequest, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == req.email.strip().lower()))
    if not u or not verify_password(req.password, u.password_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return envelope({'user_id': u.id, **issue_session(db, u.id)})


@app.post('/api/v1/auth/refresh')
def refresh_auth(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        return envelope(rotate_session(db, req.refresh_token))
    except ValueError:
        raise HTTPException(status_code=401, detail='Invalid or expired refresh token')


@app.post('/api/v1/auth/logout')
def logout_auth(
    req: LogoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.all_sessions:
        revoked = revoke_all_sessions(db, user.id)
    else:
        revoked = 1 if revoke_session(db, req.refresh_token, user.id) else 0
    return envelope({'logged_out': True, 'revoked_sessions': revoked})


@app.get('/api/v1/auth/sessions')
def active_auth_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items=list_active_sessions(db,user.id)
    return envelope({'items':items,'count':len(items)})


@app.post('/api/v1/auth/forgot-password')
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    raw = create_password_reset(db, user)
    debug = os.getenv('WAZEN_PASSWORD_RESET_DEBUG', '').lower() in {'1','true','yes'}
    delivery = os.getenv('WAZEN_PASSWORD_RESET_DELIVERY', 'NOT_CONFIGURED').upper()
    data = {
        'accepted': True,
        'delivery': delivery if user else 'GENERIC',
        'message': 'If the account exists, password reset instructions will be sent when a delivery provider is configured.',
    }
    if debug and raw:
        data['debug_reset_token'] = raw
    return envelope(data)


@app.post('/api/v1/auth/reset-password')
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        consume_password_reset(db, req.token, req.new_password)
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid or expired reset token')
    return envelope({'reset': True})


# -------- User/Profile --------
@app.get('/api/v1/users/me')
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = ensure_profile(db, user)
    return envelope({
        'id': user.id, 'email': user.email, 'first_name': user.first_name, 'language': user.language,
        'profile': {
            'height_cm': p.height_cm, 'weight_kg': p.weight_kg, 'target_weight_kg': p.target_weight_kg,
            'activity_level': p.activity_level, 'goal_type': p.goal_type, 'daily_budget': p.daily_budget,
            'target_calories': p.target_calories, 'target_protein_g': p.target_protein_g,
            'target_carbs_g': p.target_carbs_g, 'target_fat_g': p.target_fat_g,
            'target_fiber_g': p.target_fiber_g,
            'sodium_max_mg': p.sodium_max_mg, 'severe_allergens': p.severe_allergens(),
            'date_of_birth': p.date_of_birth.isoformat() if p.date_of_birth else None,
            'gender': p.gender, 'condition_context': p.condition_context(), 'food_preferences': p.food_preferences(),
            'disliked_foods': p.disliked_foods(), 'onboarding_complete': p.onboarding_complete,
        }
    })


@app.patch('/api/v1/users/me')
def update_me(req: ProfileUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = ensure_profile(db, user)
    data = req.model_dump(exclude_unset=True)
    if 'first_name' in data:
        user.first_name = data.pop('first_name')
    if 'severe_allergens' in data:
        p.severe_allergens_csv = '|'.join(sorted({x.upper() for x in data.pop('severe_allergens')}))
    if 'condition_context' in data:
        p.condition_context_csv = '|'.join(sorted({x.strip().upper() for x in data.pop('condition_context') if x.strip()}))
    if 'food_preferences' in data:
        p.food_preferences_csv = '|'.join(sorted({x.strip() for x in data.pop('food_preferences') if x.strip()}))
    if 'disliked_foods' in data:
        p.disliked_foods_csv = '|'.join(sorted({x.strip() for x in data.pop('disliked_foods') if x.strip()}))
    for k,v in data.items():
        setattr(p, k, v)
    if req.weight_kg is not None:
        record_weight(db, user.id, req.weight_kg)
    add_goal_snapshot(db, user.id, p, 'PROFILE_UPDATE')
    db.commit(); db.refresh(user); db.refresh(p)
    return me(user, db)




@app.get('/api/v1/onboarding/status')
def onboarding_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = ensure_profile(db, user)
    return envelope({'complete': p.onboarding_complete})


@app.post('/api/v1/onboarding/complete')
def complete_onboarding(req: OnboardingCompleteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = ensure_profile(db, user)
    targets = calculate_targets(req)

    if req.first_name is not None:
        user.first_name = req.first_name
    p.date_of_birth = req.date_of_birth
    p.gender = req.gender
    p.height_cm = req.height_cm
    p.weight_kg = req.weight_kg
    p.target_weight_kg = req.target_weight_kg
    p.goal_type = req.goal_type
    p.activity_level = req.activity_level
    p.daily_budget = req.daily_budget
    p.severe_allergens_csv = '|'.join(sorted({x.upper() for x in req.severe_allergens}))
    p.condition_context_csv = '|'.join(sorted({x.strip().upper() for x in req.condition_context if x.strip()}))
    p.food_preferences_csv = '|'.join(sorted({x.strip() for x in req.food_preferences if x.strip()}))
    p.disliked_foods_csv = '|'.join(sorted({x.strip() for x in req.disliked_foods if x.strip()}))
    p.target_calories = targets['target_calories']
    p.target_protein_g = targets['target_protein_g']
    p.target_carbs_g = targets['target_carbs_g']
    p.target_fat_g = targets['target_fat_g']
    p.sodium_max_mg = targets['sodium_max_mg']
    p.onboarding_complete = True
    record_weight(db, user.id, req.weight_kg)
    add_goal_snapshot(db, user.id, p, 'ONBOARDING')
    db.commit()
    db.refresh(p)
    return envelope({'complete': True, 'targets': targets, 'profile': me(user, db)['data']['profile']})




@app.get('/api/v1/profile/insights')
def get_profile_insights(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return envelope(profile_insights(db,user))


@app.post('/api/v1/profile/recalculate-plan')
def recalculate_plan(req: PlanRecalculateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p=ensure_profile(db,user)
    if not p.date_of_birth or not p.gender or not p.height_cm or not p.weight_kg:
        raise HTTPException(status_code=422, detail='Complete body profile required before recalculating plan')

    data=req.model_dump(exclude_unset=True)
    for key,value in data.items():
        setattr(p,key,value)

    from app.models.schemas import OnboardingCompleteRequest
    calc_req=OnboardingCompleteRequest(
        first_name=user.first_name,
        date_of_birth=p.date_of_birth,
        gender=p.gender,
        height_cm=p.height_cm,
        weight_kg=p.weight_kg,
        target_weight_kg=p.target_weight_kg,
        goal_type=p.goal_type,
        activity_level=p.activity_level,
        daily_budget=p.daily_budget,
        severe_allergens=p.severe_allergens(),
        condition_context=p.condition_context(),
        food_preferences=p.food_preferences(),
        disliked_foods=p.disliked_foods(),
    )
    targets=calculate_targets(calc_req)
    p.target_calories=targets['target_calories']
    p.target_protein_g=targets['target_protein_g']
    p.target_carbs_g=targets['target_carbs_g']
    p.target_fat_g=targets['target_fat_g']
    p.sodium_max_mg=targets['sodium_max_mg']
    record_weight(db, user.id, p.weight_kg)
    add_goal_snapshot(db, user.id, p, 'RECALCULATE')
    db.commit(); db.refresh(p)
    return envelope({'targets':targets,'profile':me(user,db)['data']['profile']})


@app.get('/api/v1/profile/history')
def profile_history(
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items=list_goal_history(db, user.id, limit)
    return envelope({'items':items,'count':len(items)})


@app.get('/api/v1/preferences')
def get_preferences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items=list_preferences(db,user.id)
    return envelope({'items':items,'count':len(items)})


@app.put('/api/v1/preferences')
def put_preference(
    req: PreferenceSettingRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        item=set_preference(db,user.id,req.target_type,req.target_value,req.level)
    except ValueError:
        raise HTTPException(status_code=422,detail='Invalid preference')
    return envelope(item)


@app.get('/api/v1/health-limits')
def get_health_limits(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items=list_health_limits(db,user.id)
    return envelope({'items':items,'count':len(items)})


@app.put('/api/v1/health-limits')
def put_health_limit(
    req: HealthLimitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item=set_health_limit(db,user.id,req)
    return envelope(item)


# -------- Food Log + persisted daily state --------
@app.post('/api/v1/food-log')
def add_food_log(
    req: FoodLogCreateRequest,
    idempotency_key: Optional[str] = Header(default=None, alias='Idempotency-Key'),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    idem=_begin_write_idempotency(db,user,idempotency_key,'/api/v1/food-log',req.model_dump())
    if idem['mode']=='REPLAY':
        return idem['response']
    try:
        row = FoodLog(user_id=user.id, **req.model_dump())
        db.add(row); db.commit(); db.refresh(row)
        response=envelope({'log_id': row.id, 'daily_totals': today_totals(db, user.id), 'daily_state': calculate_daily_state(build_daily_request(db, user)).model_dump()})
        finish_idempotent(db,idem.get('record'),response)
        return response
    except Exception:
        abandon_idempotent(db,idem.get('record'))
        raise


@app.get('/api/v1/food-log/today')
def food_log_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.scalars(select(FoodLog).where(FoodLog.user_id == user.id, FoodLog.logged_at >= start).order_by(FoodLog.logged_at)).all()
    return envelope({
        'items': [
            {'id':x.id,'food_id':x.food_id,'food_name':x.food_name,'meal_type':x.meal_type,'entry_method':x.entry_method,
             'calories':x.calories,'protein_g':x.protein_g,'carbs_g':x.carbs_g,'fat_g':x.fat_g,'fiber_g':x.fiber_g,'sodium_mg':x.sodium_mg,
             'logged_at':x.logged_at.isoformat()} for x in rows
        ],
        'totals': today_totals(db, user.id),
        'daily_state': calculate_daily_state(build_daily_request(db, user)).model_dump(),
    })




@app.patch('/api/v1/food-log/{log_id}')
def update_food_log(log_id: str, req: FoodLogUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(FoodLog, log_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail='Food log not found')
    data = req.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    row.entry_method = 'USER_EDITED'
    db.commit()
    db.refresh(row)
    return envelope({
        'item': {
            'id':row.id,'food_id':row.food_id,'food_name':row.food_name,
            'meal_type':row.meal_type,'entry_method':row.entry_method,
            'calories':row.calories,'protein_g':row.protein_g,'carbs_g':row.carbs_g,
            'fat_g':row.fat_g,'fiber_g':row.fiber_g,'sodium_mg':row.sodium_mg,'logged_at':row.logged_at.isoformat(),
        },
        'totals': today_totals(db,user.id),
        'daily_state': calculate_daily_state(build_daily_request(db,user)).model_dump(),
    })

@app.delete('/api/v1/food-log/{log_id}')
def delete_food_log(log_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(FoodLog, log_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail='Food log not found')
    db.delete(row); db.commit()
    return envelope({'deleted': True, 'daily_state': calculate_daily_state(build_daily_request(db, user)).model_dump()})



class FavoriteLogRequest(BaseModel):
    meal_type: Optional[Literal['BREAKFAST','LUNCH','DINNER','SNACK']] = None


def _serialize_favorite(x: FavoriteMeal):
    return {
        'id':x.id,
        'food_id':x.food_id,
        'food_name':x.food_name,
        'default_meal_type':x.default_meal_type,
        'calories':x.calories,
        'protein_g':x.protein_g,
        'carbs_g':x.carbs_g,
        'fat_g':x.fat_g,
        'fiber_g':x.fiber_g,
        'sodium_mg':x.sodium_mg,
        'created_at':x.created_at.isoformat(),
    }


@app.post('/api/v1/food-log/{log_id}/duplicate')
def duplicate_food_log(
    log_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source=db.get(FoodLog,log_id)
    if not source or source.user_id!=user.id:
        raise HTTPException(status_code=404,detail='Food log not found')
    row=FoodLog(
        user_id=user.id,
        food_id=source.food_id,
        food_name=source.food_name,
        meal_type=source.meal_type,
        entry_method='DUPLICATED',
        calories=source.calories,
        protein_g=source.protein_g,
        carbs_g=source.carbs_g,
        fat_g=source.fat_g,
        fiber_g=source.fiber_g,
        sodium_mg=source.sodium_mg,
    )
    db.add(row);db.commit();db.refresh(row)
    return envelope({
        'item':{
            'id':row.id,'food_id':row.food_id,'food_name':row.food_name,'meal_type':row.meal_type,
            'entry_method':row.entry_method,'calories':row.calories,'protein_g':row.protein_g,
            'carbs_g':row.carbs_g,'fat_g':row.fat_g,'fiber_g':row.fiber_g,'sodium_mg':row.sodium_mg,
            'logged_at':row.logged_at.isoformat(),
        },
        'totals':today_totals(db,user.id),
        'daily_state':calculate_daily_state(build_daily_request(db,user)).model_dump(),
    })


@app.post('/api/v1/food-log/{log_id}/favorite')
def favorite_food_log(
    log_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source=db.get(FoodLog,log_id)
    if not source or source.user_id!=user.id:
        raise HTTPException(status_code=404,detail='Food log not found')
    existing=db.scalar(select(FavoriteMeal).where(
        FavoriteMeal.user_id==user.id,
        FavoriteMeal.food_name==source.food_name,
        FavoriteMeal.calories==source.calories,
        FavoriteMeal.protein_g==source.protein_g,
    ))
    if existing:
        return envelope({'favorite':_serialize_favorite(existing),'created':False})
    fav=FavoriteMeal(
        user_id=user.id,
        food_id=source.food_id,
        food_name=source.food_name,
        default_meal_type=source.meal_type,
        calories=source.calories,
        protein_g=source.protein_g,
        carbs_g=source.carbs_g,
        fat_g=source.fat_g,
        sodium_mg=source.sodium_mg,
        source_log_id=source.id,
    )
    db.add(fav);db.commit();db.refresh(fav)
    return envelope({'favorite':_serialize_favorite(fav),'created':True})


@app.get('/api/v1/food-log/favorites')
def favorite_meals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows=db.scalars(select(FavoriteMeal).where(
        FavoriteMeal.user_id==user.id
    ).order_by(FavoriteMeal.created_at.desc())).all()
    return envelope({'items':[_serialize_favorite(x) for x in rows],'count':len(rows)})


@app.post('/api/v1/food-log/favorites/{favorite_id}/log')
def log_favorite_meal(
    favorite_id: str,
    req: FavoriteLogRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fav=db.get(FavoriteMeal,favorite_id)
    if not fav or fav.user_id!=user.id:
        raise HTTPException(status_code=404,detail='Favorite meal not found')
    row=FoodLog(
        user_id=user.id,
        food_id=fav.food_id,
        food_name=fav.food_name,
        meal_type=req.meal_type or fav.default_meal_type,
        entry_method='FAVORITE',
        calories=fav.calories,
        protein_g=fav.protein_g,
        carbs_g=fav.carbs_g,
        fat_g=fav.fat_g,
        fiber_g=fav.fiber_g,
        sodium_mg=fav.sodium_mg,
    )
    db.add(row);db.commit();db.refresh(row)
    return envelope({
        'item':{
            'id':row.id,'food_id':row.food_id,'food_name':row.food_name,'meal_type':row.meal_type,
            'entry_method':row.entry_method,'calories':row.calories,'protein_g':row.protein_g,
            'carbs_g':row.carbs_g,'fat_g':row.fat_g,'sodium_mg':row.sodium_mg,
            'logged_at':row.logged_at.isoformat(),
        },
        'totals':today_totals(db,user.id),
        'daily_state':calculate_daily_state(build_daily_request(db,user)).model_dump(),
    })


@app.post('/api/v1/activity-log')
def add_activity_log(
    req: ActivityLogCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row=ActivityLog(
        user_id=user.id,
        calories_credit=req.calories_credit,
        source=req.source,
        note=req.note,
    )
    db.add(row);db.commit();db.refresh(row)
    return envelope({
        'item':{
            'id':row.id,'calories_credit':row.calories_credit,'source':row.source,
            'note':row.note,'logged_at':row.logged_at.isoformat(),
        },
        'activity_credit':today_activity_credit(db,user.id),
        'daily_state':calculate_daily_state(build_daily_request(db,user)).model_dump(),
    })


@app.get('/api/v1/activity-log/today')
def activity_log_today(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    start=now.replace(hour=0,minute=0,second=0,microsecond=0)
    rows=db.scalars(select(ActivityLog).where(
        ActivityLog.user_id==user.id,
        ActivityLog.logged_at>=start,
    ).order_by(ActivityLog.logged_at)).all()
    return envelope({
        'items':[{
            'id':x.id,'calories_credit':x.calories_credit,'source':x.source,
            'note':x.note,'logged_at':x.logged_at.isoformat(),
        } for x in rows],
        'activity_credit':today_activity_credit(db,user.id),
        'daily_state':calculate_daily_state(build_daily_request(db,user)).model_dump(),
    })


@app.delete('/api/v1/activity-log/{activity_id}')
def delete_activity_log(
    activity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row=db.get(ActivityLog,activity_id)
    if not row or row.user_id!=user.id:
        raise HTTPException(status_code=404,detail='Activity log not found')
    db.delete(row);db.commit()
    return envelope({
        'deleted':True,
        'activity_credit':today_activity_credit(db,user.id),
        'daily_state':calculate_daily_state(build_daily_request(db,user)).model_dump(),
    })

@app.get('/api/v1/nutrition/today')
def nutrition_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return envelope({'totals': today_totals(db,user.id), 'daily_request': build_daily_request(db,user).model_dump(), 'daily_state': calculate_daily_state(build_daily_request(db,user)).model_dump()})


# -------- Unified Food Catalog --------
@app.get('/api/v1/foods/search')
def food_search(
    q: Optional[str] = None,
    vendor: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    food_type: Optional[str] = None,
    max_calories: Optional[float] = None,
    min_protein_g: Optional[float] = None,
    max_sodium_mg: Optional[float] = None,
    min_fiber_g: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    rows = query_foods(
        db,
        vendor=vendor,
        brand=brand,
        category=category,
        food_type=food_type,
        q=q,
        max_calories=max_calories,
        min_protein_g=min_protein_g,
        max_sodium_mg=max_sodium_mg,
        min_fiber_g=min_fiber_g,
        max_price=max_price,
        limit=limit,
    )
    return envelope({'items':[serialize_food(x) for x in rows], 'count':len(rows)})


@app.get('/api/v1/foods/{food_id}')
def food_detail(food_id: str, db: Session = Depends(get_db)):
    item = db.get(FoodItem, food_id)
    if not item:
        raise HTTPException(status_code=404, detail='Food item not found')
    return envelope(serialize_food(item))


@app.get('/api/v1/foods/barcode/{barcode}')
def food_by_barcode(barcode: str, db: Session = Depends(get_db)):
    item = db.scalar(select(FoodItem).where(FoodItem.barcode == barcode))
    return envelope({'found': bool(item), 'item': serialize_food(item) if item else None, 'allow_submission': not bool(item)})


# -------- Natural-language craving --------
class CravingRequest(BaseModel):
    text: str


@app.post('/api/v1/cravings/parse')
def parse_craving(req: CravingRequest):
    return envelope(parse_craving_text(req.text))


# -------- Stateless compatibility endpoints --------
@app.post('/api/v1/daily-state/calculate')
def daily_state(req: DailyStateRequest): return envelope(calculate_daily_state(req).model_dump())

@app.post('/api/v1/recommendations/now')
def recommendations(req: RecommendationRequest, db: Session = Depends(get_db)):
    return envelope(recommend_now(db, req))


# -------- Persisted recommendation endpoint --------
@app.post('/api/v1/recommendations/for-me')
def recommendations_for_me(req: UserRecommendationRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return envelope(recommend_for_user(
        db,
        user,
        vendor=req.vendor,
        category=req.category,
        max_calories=req.max_calories,
        min_protein_g=req.min_protein_g,
        budget_max=req.budget_max,
        allow_modifications=req.allow_modifications,
    ))




@app.get('/api/v1/recommendations/exclusions')
def recommendation_exclusions(
    reason: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items=list_exclusions(db,user.id,limit=limit,reason=reason)
    return envelope({'items':items,'count':len(items)})


@app.get('/api/v1/recommendations/decisions')
def recommendation_decisions(
    food_id: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items=list_decisions(db,user.id,limit=limit,food_id=food_id)
    return envelope({'items':items,'count':len(items),'engine_version':'v1'})


@app.post('/api/v1/recommendations/feedback')
def recommendation_feedback(req: RecommendationFeedbackRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(FoodItem, req.food_id):
        raise HTTPException(status_code=404, detail='Food item not found')
    row=RecommendationFeedback(user_id=user.id, food_id=req.food_id, action=req.action)
    db.add(row); db.commit(); db.refresh(row)
    return envelope({'saved':True,'food_id':req.food_id,'action':req.action})

@app.post('/api/v1/recommendations/make-it-fit')
def make_fit(req: MakeItFitRequest, db: Session = Depends(get_db)):
    try: return envelope(make_it_fit(db, req))
    except ValueError as exc:
        if str(exc) == 'FOOD_NOT_FOUND': raise HTTPException(status_code=404, detail='Food item not found')
        raise

@app.post('/api/v1/day/rebalance')
def rebalance(req: RebalanceRequest): return envelope(rebalance_day(req))



@app.post('/api/v1/food-log/from-catalog')
def add_food_log_from_catalog(
    req: CatalogFoodLogRequest,
    idempotency_key: Optional[str] = Header(default=None, alias='Idempotency-Key'),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    food = db.get(FoodItem, req.food_id)
    if not food:
        raise HTTPException(status_code=404, detail='Food item not found')
    if not food.nutrition or food.nutrition.calories is None:
        raise HTTPException(status_code=422, detail='Food nutrition unavailable')
    idem=_begin_write_idempotency(db,user,idempotency_key,'/api/v1/food-log/from-catalog',req.model_dump())
    if idem['mode']=='REPLAY':
        return idem['response']
    try:
        row = log_catalog_food(db, user, food, req.meal_type, req.quantity, req.entry_method)
        state = calculate_daily_state(build_daily_request(db, user)).model_dump()
        response=envelope({
            'log': {
                'id': row.id, 'food_id': row.food_id, 'food_name': row.food_name,
                'meal_type': row.meal_type, 'quantity': req.quantity, 'calories': row.calories,
                'protein_g': row.protein_g, 'carbs_g': row.carbs_g, 'fat_g': row.fat_g, 'fiber_g': row.fiber_g, 'sodium_mg': row.sodium_mg
            },
            'daily_totals': today_totals(db, user.id),
            'daily_state': state,
        })
        finish_idempotent(db,idem.get('record'),response)
        return response
    except Exception:
        abandon_idempotent(db,idem.get('record'))
        raise


@app.post('/api/v1/golden-flow')
def golden_flow(req: GoldenFlowRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    parsed=parse_craving_text(req.craving_text)

    logged = None
    if req.auto_log_food_id:
        food = db.get(FoodItem, req.auto_log_food_id)
        if not food:
            raise HTTPException(status_code=404, detail='Food item not found')
        logged_row = log_catalog_food(db, user, food, req.meal_type, req.quantity, 'RECOMMENDATION')
        logged = {
            'log_id': logged_row.id,
            'food_id': logged_row.food_id,
            'food_name': logged_row.food_name,
            'calories': logged_row.calories,
        }

    recommendations = recommend_for_user(
        db, user,
        vendor=parsed['restaurant'],
        category=parsed['food_category'],
        max_calories=parsed['max_calories'],
        min_protein_g=parsed['min_protein_g'],
        budget_max=parsed['budget_max'],
        allow_modifications=req.allow_modifications,
    )

    return envelope({
        'parsed_intent': parsed,
        'logged': logged,
        'daily_totals': today_totals(db, user.id),
        'daily_state': calculate_daily_state(build_daily_request(db, user)).model_dump(),
        'recommendations': recommendations,
    })


MAKE_IT_FIT_COMPONENTS = [
    {'component':'REGULAR_PEPSI_453ML','label_ar':'استبدال البيبسي العادي بدايت بيبسي','label_en':'Replace Regular Pepsi with Diet Pepsi','modifier_id':'KFC-MOD-001'},
    {'component':'MEDIUM_FRIES','label_ar':'تصغير البطاطس الوسط إلى عادي','label_en':'Medium Fries to Regular Fries','modifier_id':'KFC-MOD-002'},
    {'component':'LARGE_FRIES','label_ar':'تصغير البطاطس الكبير إلى عادي','label_en':'Large Fries to Regular Fries','modifier_id':'KFC-MOD-003'},
    {'component':'DYNAMITE_SAUCE_DIP','label_ar':'إزالة صوص الديناميت','label_en':'Remove Dynamite Sauce Dip','modifier_id':'KFC-MOD-004'},
    {'component':'RANCH_SAUCE_DIP','label_ar':'إزالة صوص كنتاكي رانش','label_en':'Remove Kentucky Ranch Dip','modifier_id':'KFC-MOD-005'},
]

@app.get('/api/v1/foods/{food_id}/make-it-fit-options')
def make_it_fit_options(food_id: str, db: Session = Depends(get_db)):
    food=db.get(FoodItem,food_id)
    if not food:
        raise HTTPException(status_code=404,detail='Food item not found')
    if food.vendor_name!='KFC UAE':
        return envelope({'food_id':food_id,'options':[],'note':'No verified modifier set is available for this vendor yet.'})
    options=[]
    for spec in MAKE_IT_FIT_COMPONENTS:
        modifier=db.get(FoodModifier,spec['modifier_id'])
        if modifier:
            options.append({
                **spec,
                'calorie_delta':modifier.calorie_delta,
                'protein_delta_g':modifier.protein_delta_g,
                'carbs_delta_g':modifier.carbs_delta_g,
                'fat_delta_g':modifier.fat_delta_g,
                'sodium_delta_mg':modifier.sodium_delta_mg,
                'confidence':modifier.confidence_level,
            })
    return envelope({
        'food_id':food_id,
        'options':options,
        'note':'Select only components actually included in your meal. Wazen does not assume sides, drinks or sauces.'
    })

@app.post('/api/v1/food-log/from-modified-catalog')
def add_modified_catalog_food(
    req: ModifiedCatalogFoodLogRequest,
    idempotency_key: Optional[str] = Header(default=None, alias='Idempotency-Key'),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fit=make_it_fit(db,MakeItFitRequest(
        food_id=req.food_id,
        daily_state=build_daily_request(db,user),
        included_components=req.included_components,
    ))
    food=db.get(FoodItem,req.food_id)
    idem=_begin_write_idempotency(db,user,idempotency_key,'/api/v1/food-log/from-modified-catalog',req.model_dump())
    if idem['mode']=='REPLAY':
        return idem['response']
    try:
        n=fit['modified_nutrition']; q=float(req.quantity)
        row=log_nutrition_snapshot(
            db,user,req.food_id,
            (food.name_en or food.name_ar or req.food_id)+(' - Modified' if fit['applied_modifications'] else ''),
            req.meal_type,
            calories=(n['calories'] or 0)*q,
            protein_g=(n['protein_g'] or 0)*q,
            carbs_g=(n['carbs_g'] or 0)*q,
            fat_g=(n['fat_g'] or 0)*q,
            fiber_g=(food.nutrition.fiber_g or 0)*q if food and food.nutrition else 0,
            sodium_mg=(n['sodium_mg'] or 0)*q,
        )
        response=envelope({
            'log':{
                'id':row.id,'food_id':row.food_id,'food_name':row.food_name,
                'meal_type':row.meal_type,'quantity':q,'calories':row.calories,
                'protein_g':row.protein_g,'carbs_g':row.carbs_g,'fat_g':row.fat_g,'sodium_mg':row.sodium_mg,
            },
            'make_it_fit':fit,
            'daily_totals':today_totals(db,user.id),
            'daily_state':calculate_daily_state(build_daily_request(db,user)).model_dump(),
        })
        finish_idempotent(db,idem.get('record'),response)
        return response
    except Exception:
        abandon_idempotent(db,idem.get('record'))
        raise



@app.get('/api/v1/rebalance/for-me')
def rebalance_for_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    daily_req = build_daily_request(db, user)
    state = calculate_daily_state(daily_req)

    if state.remaining_calories > 0:
        recommendation_ceiling = state.remaining_calories
        strategy = 'USE_REMAINING'
    else:
        recommendation_ceiling = max(250.0, min(600.0, daily_req.target_calories * 0.20))
        strategy = 'LIGHTER_NEXT_OPTIONS'

    recs = recommend_for_user(
        db, user,
        vendor=None,
        category=None,
        max_calories=recommendation_ceiling,
        budget_max=None,
        allow_modifications=True,
    )
    ranked_options = recs.get('results', [])
    if state.remaining_calories <= 0:
        next_options = [
            x for x in ranked_options
            if (x.get('nutrition') or {}).get('calories') is not None
            and float(x['nutrition']['calories']) <= recommendation_ceiling * 1.15
        ][:5]
    else:
        next_options = ranked_options[:5]

    if state.remaining_calories <= 0:
        headline = 'تم تحديث يومك'
        message = 'اختيارك محفوظ. إذا احتجت شيء لاحقًا، هذه خيارات أخف تساعدك تكمل يومك بدون إلغاء الوجبة اللي اخترتها.'
    elif state.protein_gap_g > 20:
        headline = 'باقي لك بروتين اليوم'
        message = f'باقي تقريبًا {state.remaining_calories:.0f} سعرة و{state.protein_gap_g:.0f}g بروتين. هذه أقرب الخيارات للمتبقي.'
    else:
        headline = 'يومك متوازن'
        message = f'باقي تقريبًا {state.remaining_calories:.0f} سعرة. هذه خيارات تناسب المساحة المتبقية.'

    return envelope({
        'daily_totals': today_totals(db, user.id),
        'daily_state': state.model_dump(),
        'headline': headline,
        'message': message,
        'user_choice_preserved': True,
        'strategy': strategy,
        'recommendation_calorie_ceiling': recommendation_ceiling,
        'next_options': next_options,
    })



TEXT_STOPWORDS = {
    'اكلت','أكلت','اكل','أكل','ابي','أبي','ابغى','أبغى','اريد','أريد','من','مع','و','في','على',
    'وجبة','سناك','فطور','غداء','عشاء','calories','kcal','سعرة','سعره','g','جرام'
}

TEXT_ALIASES = {
    'زينجر':'Zinger', 'زنجر':'Zinger',
    'بيج ماك':'Big Mac', 'بج ماك':'Big Mac',
    'ماك تشيكن':'McChicken', 'تشيكن':'Chicken',
    'برغر':'Burger', 'برجر':'Burger',
    'بطاطس':'Fries', 'فرايز':'Fries',
    'ناجتس':'Nuggets', 'نقتس':'Nuggets',
}
VENDOR_ALIASES = {
    'kfc':'KFC UAE', 'كي اف سي':'KFC UAE', 'كي إف سي':'KFC UAE',
    'mcdonald':'McDonald\'s UAE', 'ماكدونالد':'McDonald\'s UAE', 'ماكدونالدز':'McDonald\'s UAE',
    'hardee':'Hardee\'s UAE', 'هارديز':'Hardee\'s UAE',
}

def _text_catalog_candidates(db: Session, text: str, limit: int = 8):
    cleaned = re.sub(r'[^\w\u0600-\u06FF\s]+',' ',text.lower())
    vendor = next((v for k,v in VENDOR_ALIASES.items() if k in cleaned), None)
    tokens = [x for x in cleaned.split() if len(x) >= 2 and x not in TEXT_STOPWORDS and not x.isdigit()]
    alias_queries = [eng for ar,eng in TEXT_ALIASES.items() if ar in cleaned]
    seen, items = set(), []
    queries = alias_queries + sorted(tokens, key=len, reverse=True)
    for q in queries:
        for item in query_foods(db, vendor=vendor, q=q, limit=limit):
            if item.id not in seen:
                seen.add(item.id)
                items.append(serialize_food(item))
                if len(items) >= limit:
                    return items
    # If text identified a vendor but not an item, return a small vendor shortlist for review.
    if vendor and not items:
        for item in query_foods(db, vendor=vendor, limit=limit):
            if item.id not in seen:
                items.append(serialize_food(item)); seen.add(item.id)
    return items

@app.post('/api/v1/food-log/parse-text')
def parse_food_text(req: TextFoodParseRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data=parse_natural_food_text(db,req.text)
    data['meal_type']=req.meal_type
    return envelope(data)

@app.post('/api/v1/food-log/analyze-image')
def analyze_food_image_endpoint(req: ImageFoodAnalyzeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    caption_preview=parse_natural_food_text(db, req.user_caption) if req.user_caption else None
    try:
        analysis = analyze_food_image(req.image_base64, req.user_caption)
    except Exception as exc:
        return envelope({
            'status':'REVIEW_REQUIRED',
            'analysis_provider':'ERROR',
            'image_analyzed':False,
            'meal_type':req.meal_type,
            'preview_required':True,
            'auto_saved':False,
            'items':caption_preview['items'] if caption_preview else [],
            'candidates':caption_preview['candidates'] if caption_preview else [],
            'vision_result':None,
            'confidence':'UNKNOWN',
            'note':f'Vision analysis unavailable: {type(exc).__name__}. Nothing was logged automatically.'
        })

    if analysis['provider']=='NOT_CONFIGURED':
        return envelope({
            'status':'REVIEW_REQUIRED',
            'analysis_provider':'NOT_CONFIGURED',
            'image_analyzed':False,
            'meal_type':req.meal_type,
            'preview_required':True,
            'auto_saved':False,
            'items':caption_preview['items'] if caption_preview else [],
            'candidates':caption_preview['candidates'] if caption_preview else [],
            'vision_result':None,
            'confidence':'CAPTION_ONLY' if caption_preview else 'UNKNOWN',
            'note':'Vision provider is not configured. Caption matches are shown only for review; nothing is auto-saved.'
        })

    review=build_vision_review(db, analysis.get('result'))
    return envelope({
        'status':'REVIEW_REQUIRED',
        'analysis_provider':analysis['provider'],
        'analysis_model':analysis['model'],
        'image_analyzed':True,
        'meal_type':req.meal_type,
        **review,
        'vision_result':analysis.get('result'),
        'confidence':'AI_ESTIMATE',
    })



# -------- Admin Data Operations (v16) --------
class AdminReviewRequest(BaseModel):
    action: Literal['APPROVE', 'REJECT', 'FLAG']
    note: Optional[str] = None


class AdminImportRequest(BaseModel):
    format: Literal['JSON', 'CSV'] = 'JSON'
    dry_run: bool = True
    records: list[dict[str, Any]] = []
    csv_text: Optional[str] = None


class AdminFoodEditRequest(BaseModel):
    changes: dict[str, Any]


class AdminFoodMergeRequest(BaseModel):
    source_id: str
    target_id: str


def require_admin(
    x_wazen_admin_key: Optional[str] = Header(default=None),
    x_wazen_admin_actor: Optional[str] = Header(default=None),
):
    expected = os.getenv('WAZEN_ADMIN_KEY')
    if not expected:
        raise HTTPException(status_code=503, detail='Admin API is not configured')
    if not x_wazen_admin_key or not secrets.compare_digest(x_wazen_admin_key, expected):
        raise HTTPException(status_code=401, detail='Invalid admin key')
    return (x_wazen_admin_actor or 'admin').strip()[:120] or 'admin'


@app.get('/api/v1/admin/foods')
def admin_foods(
    q: Optional[str] = None,
    review_status: Optional[str] = None,
    limit: int = 50,
    actor: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items = list_admin_foods(db, q=q, review_status=review_status, limit=limit)
    return envelope({'items': items, 'count': len(items)})


@app.post('/api/v1/admin/foods/{food_id}/review')
def admin_review_food(
    food_id: str,
    req: AdminReviewRequest,
    actor: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        review = set_review(db, food_id, req.action, req.note, actor)
    except ValueError as exc:
        if str(exc) == 'FOOD_NOT_FOUND':
            raise HTTPException(status_code=404, detail='Food item not found')
        raise HTTPException(status_code=422, detail='Invalid review action')
    return envelope({
        'food_id': food_id,
        'review_status': review.review_status,
        'note': review.note,
        'reviewed_by': review.reviewed_by,
        'reviewed_at': review.reviewed_at.isoformat() if review.reviewed_at else None,
    })



@app.patch('/api/v1/admin/foods/{food_id}')
def admin_edit_food(
    food_id: str,
    req: AdminFoodEditRequest,
    actor: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        item=edit_food(db,food_id,req.changes,actor)
    except ValueError as exc:
        if str(exc)=='FOOD_NOT_FOUND':
            raise HTTPException(status_code=404,detail='Food item not found')
        raise
    return envelope(item)


@app.post('/api/v1/admin/foods/merge')
def admin_merge_foods(
    req: AdminFoodMergeRequest,
    actor: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        data=merge_foods(db,req.source_id,req.target_id,actor)
    except ValueError as exc:
        if str(exc)=='FOOD_NOT_FOUND':
            raise HTTPException(status_code=404,detail='Food item not found')
        if str(exc)=='SAME_FOOD':
            raise HTTPException(status_code=422,detail='Source and target must differ')
        raise
    return envelope(data)

@app.post('/api/v1/admin/import/foods')
def admin_import_foods(
    req: AdminImportRequest,
    actor: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        rows = parse_import_payload(req.format, req.records, req.csv_text)
    except ValueError:
        raise HTTPException(status_code=422, detail='Unsupported import format')
    summary, checked = import_foods(db, rows, req.dry_run, actor)
    return envelope({'summary': summary, 'rows': checked})


@app.get('/api/v1/admin/audit')
def admin_audit(
    limit: int = 100,
    actor: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(max(1, min(limit, 500)))
    ).all()
    return envelope({
        'items': [{
            'id': x.id,
            'action': x.action,
            'entity_type': x.entity_type,
            'entity_id': x.entity_id,
            'actor': x.actor,
            'details_json': x.details_json,
            'created_at': x.created_at.isoformat(),
        } for x in rows],
        'count': len(rows),
    })



# -------- Weekly Plan + Progress (v17) --------
@app.get('/api/v1/plan/week')
def weekly_plan(
    start_date: Optional[date] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return envelope(get_or_generate_week(db, user, start_date))
    except ValueError as exc:
        if str(exc) == 'PROFILE_REQUIRED':
            raise HTTPException(status_code=422, detail='Complete profile required')
        if str(exc) == 'NO_ELIGIBLE_FOODS':
            raise HTTPException(status_code=422, detail='No eligible foods available for this profile')
        raise


@app.post('/api/v1/plan/week/generate')
def regenerate_weekly_plan(
    start_date: Optional[date] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return envelope(generate_week(db, user, start_date or week_start_for(), replace=True))
    except ValueError as exc:
        if str(exc) == 'PROFILE_REQUIRED':
            raise HTTPException(status_code=422, detail='Complete profile required')
        if str(exc) == 'NO_ELIGIBLE_FOODS':
            raise HTTPException(status_code=422, detail='No eligible foods available for this profile')
        raise


@app.post('/api/v1/plan/day/{plan_date}/rebalance')
def rebalance_weekly_plan_day(
    plan_date: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return envelope(rebalance_plan_day(db, user, plan_date))
    except ValueError as exc:
        if str(exc) == 'PROFILE_REQUIRED':
            raise HTTPException(status_code=422, detail='Complete profile required')
        if str(exc) == 'NO_ELIGIBLE_FOODS':
            raise HTTPException(status_code=422, detail='No eligible foods available for this profile')
        raise


@app.get('/api/v1/progress')
def get_progress(
    range: Literal['week', 'month', '3months'] = 'week',
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    days = {'week': 7, 'month': 30, '3months': 90}[range]
    return envelope(progress_summary(db, user, days))
