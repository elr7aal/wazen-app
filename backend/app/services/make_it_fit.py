from sqlalchemy.orm import Session
from app.models.db_models import FoodItem, FoodModifier
from app.models.schemas import MakeItFitRequest
from app.services.daily_state import calculate_daily_state

COMPONENT_TO_MODIFIER = {
    'REGULAR_PEPSI_453ML':'KFC-MOD-001', 'MEDIUM_FRIES':'KFC-MOD-002','LARGE_FRIES':'KFC-MOD-003',
    'DYNAMITE_SAUCE_DIP':'KFC-MOD-004','RANCH_SAUCE_DIP':'KFC-MOD-005'
}


def make_it_fit(db: Session, req: MakeItFitRequest):
    item=db.get(FoodItem,req.food_id)
    if not item or not item.nutrition: raise ValueError('FOOD_NOT_FOUND')
    selected=[]
    seen_components=set()
    for component in req.included_components:
        if component in seen_components:
            continue
        seen_components.add(component)
        mid=COMPONENT_TO_MODIFIER.get(component)
        if mid:
            m=db.get(FoodModifier,mid)
            if m and m.vendor_name==item.vendor_name:
                selected.append(m)
    n=item.nutrition
    base={'calories':n.calories or 0,'protein_g':n.protein_g or 0,'carbs_g':n.carbs_g or 0,'fat_g':n.fat_g or 0,'sodium_mg':n.sodium_mg}
    modified=dict(base)
    for m in selected:
        modified['calories']=max(0,modified['calories']+(m.calorie_delta or 0))
        modified['protein_g']=max(0,modified['protein_g']+(m.protein_delta_g or 0))
        modified['carbs_g']=max(0,modified['carbs_g']+(m.carbs_delta_g or 0))
        modified['fat_g']=max(0,modified['fat_g']+(m.fat_delta_g or 0))
        modified['sodium_mg']=(max(0,modified['sodium_mg']+m.sodium_delta_mg)
            if modified['sodium_mg'] is not None and m.sodium_delta_mg is not None else None)
    daily=calculate_daily_state(req.daily_state)
    delta={k:round(modified[k]-base[k],1) if modified[k] is not None and base[k] is not None else None for k in base}
    return {
        'food_id':item.id,
        'name':item.name_en or item.name_ar,
        'core_food_unchanged':True,
        'base_nutrition':{k:round(v,1) if v is not None else None for k,v in base.items()},
        'modified_nutrition':{k:round(v,1) if v is not None else None for k,v in modified.items()},
        'nutrition_delta':delta,
        'calories_saved':round(base['calories']-modified['calories'],1),
        'fits_remaining_calories':modified['calories']<=daily.remaining_calories,
        'remaining_calories_before_meal':daily.remaining_calories,
        'applied_modifications':[{
            'id':m.id,
            'name':m.name_en,
            'confidence':m.confidence_level
        } for m in selected],
        'note':'Only verified component changes explicitly included in the request are applied. The requested core food is preserved.'
    }

