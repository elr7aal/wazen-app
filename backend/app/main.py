import os
import re
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db, SessionLocal
from app.models.db_models import User, UserProfile, FoodLog, FoodItem, RecommendationFeedback
from app.models.schemas import (
    RegisterRequest, LoginRequest, ProfileUpdateRequest, FoodLogCreateRequest,
    FoodLogUpdateRequest, OnboardingCompleteRequest, PlanRecalculateRequest,
    UserRecommendationRequest, CatalogFoodLogRequest, GoldenFlowRequest,
    RecommendationFeedbackRequest, TextFoodParseRequest
)
from app.security import hash_password, verify_password, create_access_token
from app.deps import get_current_user
from app.services.catalog import ensure_catalog_seeded, query_foods, serialize_food
from app.services.persistence import ensure_profile, build_daily_request, today_totals, recommend_for_user, log_catalog_food
from app.services.daily_state import calculate_daily_state
from app.services.onboarding import calculate_targets
from app.services.profile_insights import profile_insights

Base.metadata.create_all(bind=engine)
with SessionLocal() as _db:
    ensure_catalog_seeded(_db)

app = FastAPI(title="WAZEN API", version="0.5.0-alpha")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("WAZEN_CORS_ORIGINS","*").split(",") if x.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def envelope(data=None,error=None,meta=None):
    return {"success":error is None,"data":data,"error":error,"meta":meta or {}}

@app.get("/api/v1/health")
def health():
    return envelope({"status":"ok","service":"wazen-api","version":"0.5.0-alpha"})

@app.post("/api/v1/auth/register")
def register(req:RegisterRequest,db:Session=Depends(get_db)):
    email=req.email.strip().lower()
    if "@" not in email: raise HTTPException(status_code=422,detail="Valid email required")
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(status_code=409,detail="Email already registered")
    u=User(email=email,password_hash=hash_password(req.password),first_name=req.first_name,language=req.language)
    db.add(u); db.flush(); db.add(UserProfile(user_id=u.id)); db.commit(); db.refresh(u)
    return envelope({"user_id":u.id,"access_token":create_access_token(u.id),"token_type":"bearer"})

@app.post("/api/v1/auth/login")
def login(req:LoginRequest,db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.email==req.email.strip().lower()))
    if not u or not verify_password(req.password,u.password_hash):
        raise HTTPException(status_code=401,detail="Invalid credentials")
    return envelope({"user_id":u.id,"access_token":create_access_token(u.id),"token_type":"bearer"})

def profile_payload(user,p):
    return {
        "id":user.id,"email":user.email,"first_name":user.first_name,"language":user.language,
        "profile":{
            "height_cm":p.height_cm,"weight_kg":p.weight_kg,"target_weight_kg":p.target_weight_kg,
            "activity_level":p.activity_level,"goal_type":p.goal_type,"daily_budget":p.daily_budget,
            "target_calories":p.target_calories,"target_protein_g":p.target_protein_g,
            "target_carbs_g":p.target_carbs_g,"target_fat_g":p.target_fat_g,"sodium_max_mg":p.sodium_max_mg,
            "severe_allergens":p.severe_allergens(),"date_of_birth":p.date_of_birth.isoformat() if p.date_of_birth else None,
            "gender":p.gender,"food_preferences":p.food_preferences(),"disliked_foods":p.disliked_foods(),
            "onboarding_complete":p.onboarding_complete
        }
    }

@app.get("/api/v1/users/me")
def me(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return envelope(profile_payload(user,ensure_profile(db,user)))

@app.patch("/api/v1/users/me")
def update_me(req:ProfileUpdateRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    p=ensure_profile(db,user); data=req.model_dump(exclude_unset=True)
    if "first_name" in data: user.first_name=data.pop("first_name")
    if "severe_allergens" in data: p.severe_allergens_csv="|".join(sorted({x.upper() for x in data.pop("severe_allergens")}))
    if "food_preferences" in data: p.food_preferences_csv="|".join(sorted({x.strip() for x in data.pop("food_preferences") if x.strip()}))
    if "disliked_foods" in data: p.disliked_foods_csv="|".join(sorted({x.strip() for x in data.pop("disliked_foods") if x.strip()}))
    for k,v in data.items(): setattr(p,k,v)
    db.commit(); return envelope(profile_payload(user,p))

@app.get("/api/v1/onboarding/status")
def onboarding_status(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return envelope({"complete":ensure_profile(db,user).onboarding_complete})

@app.post("/api/v1/onboarding/complete")
def onboarding_complete(req:OnboardingCompleteRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    p=ensure_profile(db,user); t=calculate_targets(req)
    if req.first_name is not None: user.first_name=req.first_name
    p.date_of_birth=req.date_of_birth; p.gender=req.gender; p.height_cm=req.height_cm; p.weight_kg=req.weight_kg
    p.target_weight_kg=req.target_weight_kg; p.goal_type=req.goal_type; p.activity_level=req.activity_level; p.daily_budget=req.daily_budget
    p.severe_allergens_csv="|".join(sorted({x.upper() for x in req.severe_allergens}))
    p.food_preferences_csv="|".join(sorted({x.strip() for x in req.food_preferences if x.strip()}))
    p.disliked_foods_csv="|".join(sorted({x.strip() for x in req.disliked_foods if x.strip()}))
    p.target_calories=t["target_calories"]; p.target_protein_g=t["target_protein_g"]; p.target_carbs_g=t["target_carbs_g"]; p.target_fat_g=t["target_fat_g"]; p.sodium_max_mg=t["sodium_max_mg"]; p.onboarding_complete=True
    db.commit()
    return envelope({"complete":True,"targets":t,"profile":profile_payload(user,p)["profile"]})

@app.post("/api/v1/profile/recalculate-plan")
def recalc(req:PlanRecalculateRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    p=ensure_profile(db,user)
    for k,v in req.model_dump(exclude_unset=True).items(): setattr(p,k,v)
    if not p.date_of_birth or not p.gender or not p.height_cm or not p.weight_kg:
        raise HTTPException(status_code=422,detail="Complete body profile required")
    calc=OnboardingCompleteRequest(
        first_name=user.first_name,date_of_birth=p.date_of_birth,gender=p.gender,height_cm=p.height_cm,weight_kg=p.weight_kg,
        target_weight_kg=p.target_weight_kg,goal_type=p.goal_type,activity_level=p.activity_level,daily_budget=p.daily_budget,
        severe_allergens=p.severe_allergens(),food_preferences=p.food_preferences(),disliked_foods=p.disliked_foods()
    )
    t=calculate_targets(calc)
    p.target_calories=t["target_calories"]; p.target_protein_g=t["target_protein_g"]; p.target_carbs_g=t["target_carbs_g"]; p.target_fat_g=t["target_fat_g"]; p.sodium_max_mg=t["sodium_max_mg"]
    db.commit(); return envelope({"targets":t,"profile":profile_payload(user,p)["profile"]})

@app.get("/api/v1/profile/insights")
def insights(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return envelope(profile_insights(db,user))

@app.get("/api/v1/nutrition/today")
def nutrition_today(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    req=build_daily_request(db,user)
    return envelope({"totals":today_totals(db,user.id),"daily_request":req.model_dump(),"daily_state":calculate_daily_state(req).model_dump()})

@app.post("/api/v1/food-log")
def food_log(req:FoodLogCreateRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=FoodLog(user_id=user.id,**req.model_dump()); db.add(row); db.commit(); db.refresh(row)
    return envelope({"log_id":row.id,"daily_totals":today_totals(db,user.id),"daily_state":calculate_daily_state(build_daily_request(db,user)).model_dump()})

@app.get("/api/v1/food-log/today")
def food_log_today(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    start=datetime.now(timezone.utc).replace(tzinfo=None,hour=0,minute=0,second=0,microsecond=0)
    rows=db.scalars(select(FoodLog).where(FoodLog.user_id==user.id,FoodLog.logged_at>=start).order_by(FoodLog.logged_at)).all()
    return envelope({"items":[{"id":x.id,"food_id":x.food_id,"food_name":x.food_name,"meal_type":x.meal_type,"entry_method":x.entry_method,"calories":x.calories,"protein_g":x.protein_g,"carbs_g":x.carbs_g,"fat_g":x.fat_g,"sodium_mg":x.sodium_mg,"logged_at":x.logged_at.isoformat()} for x in rows],"totals":today_totals(db,user.id),"daily_state":calculate_daily_state(build_daily_request(db,user)).model_dump()})

@app.patch("/api/v1/food-log/{log_id}")
def food_log_update(log_id:str,req:FoodLogUpdateRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=db.get(FoodLog,log_id)
    if not row or row.user_id!=user.id: raise HTTPException(status_code=404,detail="Food log not found")
    for k,v in req.model_dump(exclude_unset=True).items(): setattr(row,k,v)
    row.entry_method="USER_EDITED"; db.commit()
    return envelope({"daily_state":calculate_daily_state(build_daily_request(db,user)).model_dump()})

@app.delete("/api/v1/food-log/{log_id}")
def food_log_delete(log_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=db.get(FoodLog,log_id)
    if not row or row.user_id!=user.id: raise HTTPException(status_code=404,detail="Food log not found")
    db.delete(row); db.commit()
    return envelope({"deleted":True,"daily_state":calculate_daily_state(build_daily_request(db,user)).model_dump()})

@app.post("/api/v1/food-log/from-catalog")
def food_log_from_catalog(req:CatalogFoodLogRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    food=db.get(FoodItem,req.food_id)
    if not food or not food.nutrition: raise HTTPException(status_code=404,detail="Food item not found")
    row=log_catalog_food(db,user,food,req.meal_type,req.quantity,req.entry_method)
    return envelope({"log":{"id":row.id,"food_id":row.food_id,"food_name":row.food_name,"meal_type":row.meal_type,"calories":row.calories},"daily_totals":today_totals(db,user.id),"daily_state":calculate_daily_state(build_daily_request(db,user)).model_dump()})

@app.get("/api/v1/foods/search")
def foods_search(q:Optional[str]=None,vendor:Optional[str]=None,category:Optional[str]=None,max_calories:Optional[float]=None,min_protein_g:Optional[float]=None,limit:int=25,db:Session=Depends(get_db)):
    rows=query_foods(db,vendor=vendor,category=category,q=q,max_calories=max_calories,min_protein_g=min_protein_g,limit=limit)
    return envelope({"items":[serialize_food(x) for x in rows],"count":len(rows)})

@app.get("/api/v1/foods/{food_id}")
def food_detail(food_id:str,db:Session=Depends(get_db)):
    food=db.get(FoodItem,food_id)
    if not food: raise HTTPException(status_code=404,detail="Food item not found")
    return envelope(serialize_food(food))

@app.get("/api/v1/foods/barcode/{barcode}")
def barcode(barcode:str,db:Session=Depends(get_db)):
    item=db.scalar(select(FoodItem).where(FoodItem.barcode==barcode))
    return envelope({"found":bool(item),"item":serialize_food(item) if item else None,"allow_submission":not bool(item)})

@app.post("/api/v1/recommendations/for-me")
def recommendations(req:UserRecommendationRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return envelope(recommend_for_user(db,user,req.vendor,req.category,req.max_calories,req.budget_max,req.allow_modifications))

@app.post("/api/v1/recommendations/feedback")
def feedback(req:RecommendationFeedbackRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if not db.get(FoodItem,req.food_id): raise HTTPException(status_code=404,detail="Food item not found")
    row=RecommendationFeedback(user_id=user.id,food_id=req.food_id,action=req.action); db.add(row); db.commit()
    return envelope({"saved":True,"food_id":req.food_id,"action":req.action})

def parse_craving(text:str):
    t=text.lower(); restaurant=None; category=None
    if "هارديز" in t or "hardee" in t: restaurant="Hardee's UAE"
    elif "كي اف سي" in t or "كي إف سي" in t or "kfc" in t: restaurant="KFC UAE"
    elif "ماكدونالد" in t or "mcdonald" in t: restaurant="McDonald's UAE"
    if any(x in t for x in ["برغر","برجر","burger","زنجر","zinger"]): category="BURGERS"
    return restaurant,category,None

@app.post("/api/v1/golden-flow")
def golden(req:GoldenFlowRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    restaurant,category,max_calories=parse_craving(req.craving_text)
    recs=recommend_for_user(db,user,restaurant,category,max_calories,None,req.allow_modifications)
    return envelope({"parsed_intent":{"intent":"EAT_NOW","restaurant":restaurant,"food_category":category,"max_calories":max_calories},"logged":None,"daily_totals":today_totals(db,user.id),"daily_state":calculate_daily_state(build_daily_request(db,user)).model_dump(),"recommendations":recs})

@app.get("/api/v1/rebalance/for-me")
def rebalance(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    state=calculate_daily_state(build_daily_request(db,user))
    recs=recommend_for_user(db,user,max_calories=state.remaining_calories if state.remaining_calories>0 else None)
    return envelope({"daily_totals":today_totals(db,user.id),"daily_state":state.model_dump(),"headline":"تم تحديث يومك","message":f"باقي تقريبًا {state.remaining_calories:.0f} سعرة.","next_options":recs.get("results",[])[:5]})

@app.post("/api/v1/food-log/parse-text")
def parse_text(req:TextFoodParseRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    words=[x for x in re.sub(r"[^\w\u0600-\u06FF\s]+"," ",req.text).split() if len(x)>=2]
    found=[]; seen=set()
    for q in words:
        for item in query_foods(db,q=q,limit=8):
            if item.id not in seen:
                seen.add(item.id); found.append(serialize_food(item))
    return envelope({"input":req.text,"meal_type":req.meal_type,"status":"MATCHES_FOUND" if found else "REVIEW_REQUIRED","candidates":found[:8],"confidence":"CATALOG_MATCH" if found else "UNKNOWN"})

class ImageReq(BaseModel):
    image_base64:str
    user_caption:Optional[str]=None
    meal_type:str="SNACK"

@app.post("/api/v1/food-log/analyze-image")
def image_analysis(req:ImageReq,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return envelope({"status":"REVIEW_REQUIRED","analysis_provider":"NOT_CONFIGURED","meal_type":req.meal_type,"candidates":[],"vision_result":None,"confidence":"UNKNOWN","note":"Image AI will be enabled after the first alpha deployment."})
