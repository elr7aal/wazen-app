from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.schemas import RecommendationRequest
from app.services.catalog import query_foods
from app.services.daily_state import calculate_daily_state


def _norm(v: str | None) -> str | None:
    return v.strip().lower() if v else None


def _calorie_fit(food_calories: float, remaining: float) -> float:
    if remaining <= 0: return 0.0
    return max(0.0, 100.0 - abs(food_calories - remaining) / remaining * 100.0)


def _protein_fit(protein: float, gap: float) -> float:
    if gap <= 0: return 100.0
    return min(100.0, protein / gap * 100.0)

FOOD_TERM_ALIASES = {
    'CHICKEN': {'CHICKEN','ZINGER','TWISTER','TENDERS','NUGGETS','MCCHICKEN','MCWINGS'},
    'BEEF': {'BEEF','BURGER','BIG MAC','MCROYALE','CHEESEBURGER'},
    'FISH': {'FISH','TUNA','FILET-O-FISH'},
    'RICE': {'RICE','RIZO','MACHBOOS','MANDI','BIRYANI'},
    'BURGERS': {'BURGER','BURGERS','ZINGER','BIG MAC','MCROYALE'},
    'YOGURT': {'YOGURT','YOGHURT','زبادي'},
    'OATS': {'OAT','OATS','OATMEAL','شوفان'},
    'MUSHROOM': {'MUSHROOM','مشروم'},
    'SPICY': {'SPICY','HOT','حار'},
}

def _food_text(item) -> str:
    return ' '.join([
        item.name_en or '', item.name_ar or '', item.category or '',
        item.brand_name or '', item.vendor_name or ''
    ]).upper()

def _term_matches(term: str, text: str) -> bool:
    t=term.upper().strip()
    if not t:
        return False
    if t in text:
        return True
    return any(alias in text for alias in FOOD_TERM_ALIASES.get(t,set()))

def _preference_score(item, req):
    text=_food_text(item)
    pref_hits=sum(1 for x in req.preferred_terms if _term_matches(x,text))
    dislike_hits=sum(1 for x in req.disliked_terms if _term_matches(x,text))
    behavior=float(req.behavior_scores.get(item.id,0.0))
    score=80.0 + min(15.0,pref_hits*7.5) - min(25.0,dislike_hits*12.5) + max(-15.0,min(12.0,behavior))
    return max(0.0,min(100.0,score)), pref_hits, dislike_hits, behavior


def recommend_now(db: Session, req: RecommendationRequest) -> Dict[str, Any]:
    daily = calculate_daily_state(req.daily_state)
    hard_max_calories = req.max_calories
    candidates = query_foods(db, vendor=req.vendor, category=req.category, limit=100)
    results: List[Dict[str, Any]]=[]; excluded=[]
    severe={a.upper() for a in req.severe_allergens}

    for item in candidates:
        n=item.nutrition
        if not n or n.calories is None:
            excluded.append({'food_id':item.id,'reason':'INSUFFICIENT_NUTRITION_DATA'}); continue
        contains_allergens={a.allergen_code for a in item.allergens if a.relationship_type == 'CONTAINS'}
        warning_allergens={a.allergen_code for a in item.allergens if a.relationship_type != 'CONTAINS'}
        if contains_allergens.intersection(severe):
            excluded.append({'food_id':item.id,'reason':'SEVERE_ALLERGY'}); continue
        if item.availability_status in {'UNAVAILABLE','OUT_OF_STOCK'}:
            excluded.append({'food_id':item.id,'reason':'UNAVAILABLE'}); continue

        protein=n.protein_g or 0.0; sodium=n.sodium_mg or 0.0
        calorie_fit=_calorie_fit(n.calories,daily.remaining_calories)
        protein_fit=_protein_fit(protein,daily.protein_gap_g)
        nutrition_score=calorie_fit*.6+protein_fit*.4
        health_score=100.0; warnings=[]
        if warning_allergens.intersection(severe): warnings.append('ALLERGEN_CROSS_CONTACT_WARNING')
        if daily.sodium_remaining_mg is not None and n.sodium_mg is not None and sodium>daily.sodium_remaining_mg:
            health_score=70.0; warnings.append('HIGH_SODIUM_FOR_REMAINING_DAY')
        preference_score, pref_hits, dislike_hits, behavior_score = _preference_score(item, req)
        price_score=70.0
        if req.budget_max is not None and item.price is not None:
            price_score=100.0 if item.price<=req.budget_max else max(0.0,100.0-(item.price-req.budget_max)/max(1,req.budget_max)*100)
            if item.price>req.budget_max: warnings.append('OVER_BUDGET')
        score=nutrition_score*.30+health_score*.20+preference_score*.20+price_score*.10+80*.10+100*.05+75*.05

        calorie_limit=hard_max_calories if hard_max_calories is not None else daily.remaining_calories
        if n.calories<=calorie_limit: decision='ELIGIBLE'
        elif n.calories<=calorie_limit*1.15: decision='NEAR_MATCH'
        else: decision='MAKE_IT_FIT' if req.allow_modifications else 'OVER_TARGET'
        reasons=[]
        if pref_hits>0: reasons.append('Matches your stated food preferences')
        if behavior_score>=4: reasons.append('Similar to foods you often choose')
        if dislike_hits>0: reasons.append('Contains a food type you usually avoid')
        reasons.append('Fits the requested calorie context' if decision=='ELIGIBLE' else 'Close to the requested calorie limit' if decision=='NEAR_MATCH' else 'Above the requested calorie context; modification may help')
        if protein>=daily.protein_gap_g and daily.protein_gap_g>0: reasons.append('Covers the remaining protein gap')
        elif daily.protein_gap_g>0: reasons.append('Contributes to the remaining protein target')

        source=item.sources[0] if item.sources else None
        results.append({
            'food_id':item.id,'vendor':item.vendor_name,'name':item.name_en or item.name_ar,'name_ar':item.name_ar,'category':item.category,
            'nutrition':{'calories':n.calories,'protein_g':n.protein_g,'carbs_g':n.carbs_g,'fat_g':n.fat_g,'sodium_mg':n.sodium_mg},
            'price':item.price,'currency':item.currency,'source_confidence':source.confidence_level if source else None,
            'scores':{'nutrition':round(nutrition_score,1),'health':round(health_score,1),'preference':round(preference_score,1),'wazen':round(score,1)},
            'decision':decision,'reasons':reasons,'warnings':warnings,'can_modify':req.allow_modifications and decision in {'NEAR_MATCH','MAKE_IT_FIT'}
        })
    priority={'ELIGIBLE':0,'NEAR_MATCH':1,'MAKE_IT_FIT':2,'OVER_TARGET':3}
    results.sort(key=lambda r:(priority.get(r['decision'],9),-r['scores']['wazen']))
    return {'daily_state':daily.model_dump(),'results':results,'excluded':excluded,'catalog_candidates':len(candidates)}
