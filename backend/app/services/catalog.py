import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload
from app.models.db_models import FoodItem, FoodNutrition, FoodAllergen, FoodDataSource, FoodModifier

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
SEED_FILE = DATA_DIR / 'catalog_seed_v5.json'


SEARCH_SYNONYMS = {
    'برغر': ['burger','burgers','برجر'],
    'برجر': ['burger','burgers','برغر'],
    'burger': ['burger','burgers','برغر','برجر'],
    'دجاج': ['chicken','chickenburger','mcchicken','zinger','twister','tenders','nuggets'],
    'chicken': ['chicken','دجاج'],
    'زنجر': ['zinger','زنجر'],
    'zinger': ['zinger','زنجر'],
    'بطاطس': ['fries','chips','بطاطا','بطاطس'],
    'بطاطا': ['fries','chips','بطاطس','بطاطا'],
    'fries': ['fries','بطاطس','بطاطا'],
    'سمك': ['fish','tuna','سلمون'],
    'fish': ['fish','سمك'],
    'تونة': ['tuna','تونه'],
    'tuna': ['tuna','تونة','تونه'],
    'سلطة': ['salad','سلطه'],
    'salad': ['salad','سلطة','سلطه'],
    'رز': ['rice','أرز','ارز'],
    'أرز': ['rice','رز','ارز'],
    'rice': ['rice','رز','أرز','ارز'],
    'حلا': ['dessert','sweet','حلويات'],
    'حلويات': ['dessert','sweet','حلا'],
    'dessert': ['dessert','sweet','حلا','حلويات'],
}

def _search_terms(q: str) -> list[str]:
    raw=' '.join((q or '').strip().lower().split())
    if not raw:
        return []
    terms={raw}
    for token in raw.split():
        terms.add(token)
        terms.update(SEARCH_SYNONYMS.get(token,[]))
    return sorted({x for x in terms if x}, key=len, reverse=True)



def _f(v):
    if v in (None, ''):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _split_allergens(v):
    return sorted({x.strip().upper() for x in (v or '').split('|') if x and x.strip()})


def _date(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v))
    except ValueError:
        return None


def ensure_catalog_seeded(db: Session) -> dict:
    existing = db.scalar(select(FoodItem.id).limit(1))
    if existing:
        return {'seeded': False, 'reason': 'catalog_not_empty'}
    return import_seed(db)


def import_seed(db: Session) -> dict:
    payload = json.loads(SEED_FILE.read_text(encoding='utf-8'))
    created_foods = 0
    created_modifiers = 0

    for row in payload.get('foods', []):
        fid = row.get('record_id')
        if not fid or db.get(FoodItem, fid):
            continue
        item = FoodItem(
            id=fid,
            name_en=row.get('item_name_en'), name_ar=row.get('item_name_ar'),
            food_type=row.get('vendor_type') or 'GENERIC_FOOD',
            brand_name=row.get('brand_name'), vendor_name=row.get('brand_name'), category=row.get('category'),
            serving_size=_f(row.get('serving_size')), serving_unit=row.get('serving_unit'),
            barcode=row.get('barcode') or None, price=_f(row.get('price')), currency=row.get('currency') or 'AED',
            availability_status=row.get('availability_status') or 'UNKNOWN', status='ACTIVE',
        )
        db.add(item); db.flush()
        db.add(FoodNutrition(
            food_id=fid, calories=_f(row.get('calories_kcal')), protein_g=_f(row.get('protein_g')),
            carbs_g=_f(row.get('carbs_g')), fat_g=_f(row.get('fat_g')), saturated_fat_g=_f(row.get('saturated_fat_g')),
            fiber_g=_f(row.get('fiber_g')), sugar_g=_f(row.get('sugar_g')), added_sugar_g=_f(row.get('added_sugar_g')),
            sodium_mg=_f(row.get('sodium_mg')), cholesterol_mg=_f(row.get('cholesterol_mg')),
        ))
        for allergen in _split_allergens(row.get('allergens')):
            db.add(FoodAllergen(food_id=fid, allergen_code=allergen, relationship_type='CONTAINS'))
        db.add(FoodDataSource(
            food_id=fid, source_type=row.get('source_type') or 'UNKNOWN', source_name=row.get('source_name'),
            source_reference=row.get('source_reference'), source_market=row.get('source_market'),
            confidence_level=row.get('confidence_level'), verified_at=_date(row.get('verified_date')),
        ))
        created_foods += 1

    for row in payload.get('grocery', []):
        fid = row.get('record_id')
        if not fid or db.get(FoodItem, fid):
            continue
        item = FoodItem(
            id=fid, name_en=row.get('product_name_en'), name_ar=row.get('product_name_ar'),
            food_type='GROCERY', brand_name=row.get('brand'), vendor_name=row.get('retailer'), category=row.get('category'),
            serving_size=_f(row.get('serving_size')), serving_unit=row.get('serving_unit'), barcode=row.get('barcode') or None,
            price=_f(row.get('offer_price')) if _f(row.get('offer_price')) is not None else _f(row.get('price')),
            currency=row.get('currency') or 'AED', availability_status=row.get('stock_status') or 'UNKNOWN', status='ACTIVE',
        )
        db.add(item); db.flush()
        db.add(FoodNutrition(
            food_id=fid, calories=_f(row.get('calories_per_serving')), protein_g=_f(row.get('protein_g')),
            carbs_g=_f(row.get('carbs_g')), fat_g=_f(row.get('fat_g')), fiber_g=_f(row.get('fiber_g')),
            sugar_g=_f(row.get('sugar_g')), sodium_mg=_f(row.get('sodium_mg')),
        ))
        # Grocery allergens are conservatively derived only from explicit notes in this alpha seed.
        notes=(row.get('notes') or '').lower()
        note_map={'milk':'MILK','egg':'EGG','fish':'FISH','peanut':'PEANUT','gluten':'GLUTEN','soy':'SOY','sesame':'SESAME'}
        for key, code in note_map.items():
            if key in notes:
                rel = 'MAY_CONTAIN' if ('may contain' in notes or 'warning' in notes) else 'CONTAINS'
                db.add(FoodAllergen(food_id=fid, allergen_code=code, relationship_type=rel))
        db.add(FoodDataSource(
            food_id=fid, source_type=row.get('source_type') or 'UNKNOWN', source_name=row.get('source_name'),
            source_reference=row.get('source_reference'), source_market='UAE', confidence_level=row.get('confidence_level')
        ))
        created_foods += 1

    for row in payload.get('modifiers', []):
        mid = row.get('modifier_id')
        if not mid or db.get(FoodModifier, mid) or str(mid).startswith('MOD-00'):
            continue
        db.add(FoodModifier(
            id=mid, vendor_name=row.get('brand') or '', menu_item_name=row.get('menu_item'),
            modifier_group=row.get('modifier_group') or 'OTHER', name_en=row.get('modifier_name_en') or mid,
            name_ar=row.get('modifier_name_ar'), action=row.get('action') or 'UNKNOWN',
            calorie_delta=_f(row.get('calorie_delta')), protein_delta_g=_f(row.get('protein_delta_g')),
            carbs_delta_g=_f(row.get('carbs_delta_g')), fat_delta_g=_f(row.get('fat_delta_g')),
            sugar_delta_g=_f(row.get('sugar_delta_g')), sodium_delta_mg=_f(row.get('sodium_delta_mg')),
            price_delta=_f(row.get('price_delta')), confidence_level=row.get('confidence_level')
        ))
        created_modifiers += 1

    db.commit()
    return {'seeded': True, 'foods': created_foods, 'modifiers': created_modifiers}


def query_foods(
    db: Session,
    vendor=None,
    brand=None,
    category=None,
    food_type=None,
    q=None,
    max_calories=None,
    min_protein_g=None,
    max_sodium_mg=None,
    min_fiber_g=None,
    max_price=None,
    limit=50,
):
    stmt = select(FoodItem).options(
        selectinload(FoodItem.nutrition), selectinload(FoodItem.allergens), selectinload(FoodItem.sources)
    ).where(FoodItem.status == 'ACTIVE')
    if vendor:
        stmt = stmt.where(FoodItem.vendor_name.ilike(vendor))
    if brand:
        stmt = stmt.where(FoodItem.brand_name.ilike(brand))
    if category:
        stmt = stmt.where(FoodItem.category == category.upper())
    if food_type:
        stmt = stmt.where(FoodItem.food_type == food_type.upper())
    if max_price is not None:
        stmt = stmt.where(FoodItem.price.is_not(None), FoodItem.price <= max_price)
    if q:
        clauses=[]
        for term in _search_terms(q):
            like=f'%{term}%'
            clauses.extend([
                FoodItem.name_en.ilike(like),
                FoodItem.name_ar.ilike(like),
                FoodItem.brand_name.ilike(like),
                FoodItem.vendor_name.ilike(like),
                FoodItem.category.ilike(like),
            ])
        if clauses:
            stmt = stmt.where(or_(*clauses))
    if any(x is not None for x in [max_calories,min_protein_g,max_sodium_mg,min_fiber_g]):
        stmt = stmt.join(FoodNutrition, FoodNutrition.food_id == FoodItem.id)
        if max_calories is not None:
            stmt = stmt.where(FoodNutrition.calories.is_not(None),FoodNutrition.calories <= max_calories)
        if min_protein_g is not None:
            stmt = stmt.where(FoodNutrition.protein_g.is_not(None),FoodNutrition.protein_g >= min_protein_g)
        if max_sodium_mg is not None:
            stmt = stmt.where(FoodNutrition.sodium_mg.is_not(None),FoodNutrition.sodium_mg <= max_sodium_mg)
        if min_fiber_g is not None:
            stmt = stmt.where(FoodNutrition.fiber_g.is_not(None),FoodNutrition.fiber_g >= min_fiber_g)
    return list(db.scalars(stmt.limit(min(max(1,limit),100))).unique().all())


def serialize_food(item: FoodItem):
    n=item.nutrition
    source=item.sources[0] if item.sources else None
    return {
        'food_id':item.id, 'vendor':item.vendor_name, 'brand':item.brand_name,
        'name':item.name_en or item.name_ar, 'name_ar':item.name_ar, 'category':item.category,
        'food_type':item.food_type, 'serving_size':item.serving_size, 'serving_unit':item.serving_unit,
        'price':item.price, 'currency':item.currency, 'availability_status':item.availability_status,
        'nutrition': {
            'calories': n.calories if n else None, 'protein_g': n.protein_g if n else None,
            'carbs_g': n.carbs_g if n else None, 'fat_g': n.fat_g if n else None,
            'fiber_g': n.fiber_g if n else None, 'sugar_g': n.sugar_g if n else None,
            'sodium_mg': n.sodium_mg if n else None,
        },
        'allergens':[a.allergen_code for a in item.allergens],
        'source_confidence': source.confidence_level if source else None,
        'source_reference': source.source_reference if source else None,
    }
