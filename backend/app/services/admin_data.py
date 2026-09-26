import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.db_models import (
    FoodItem, FoodNutrition, FoodReview, AdminAuditLog, FoodAllergen, FoodDataSource,
    FoodLog, RecommendationFeedback, WeeklyPlanItem, FavoriteMeal,
    RecommendationExclusionLog, RecommendationDecisionLog,
)


REVIEW_ACTIONS = {'APPROVE', 'REJECT', 'FLAG'}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def audit(db: Session, action: str, entity_type: str, entity_id: str | None, actor: str, details: dict[str, Any]):
    row = AdminAuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        details_json=json.dumps(details, ensure_ascii=False, default=str),
    )
    db.add(row)
    return row


def set_review(db: Session, food_id: str, action: str, note: str | None, actor: str):
    action = action.upper()
    if action not in REVIEW_ACTIONS:
        raise ValueError('INVALID_REVIEW_ACTION')
    food = db.get(FoodItem, food_id)
    if not food:
        raise ValueError('FOOD_NOT_FOUND')
    review = db.get(FoodReview, food_id)
    if not review:
        review = FoodReview(food_id=food_id)
        db.add(review)
    review.review_status = action
    review.note = note
    review.reviewed_by = actor
    review.reviewed_at = utcnow()
    audit(db, f'FOOD_{action}', 'FOOD', food_id, actor, {'note': note})
    db.commit()
    db.refresh(review)
    return review


def serialize_review(review: FoodReview | None):
    if not review:
        return {'review_status': 'PENDING', 'note': None, 'reviewed_by': None, 'reviewed_at': None}
    return {
        'review_status': review.review_status,
        'note': review.note,
        'reviewed_by': review.reviewed_by,
        'reviewed_at': review.reviewed_at.isoformat() if review.reviewed_at else None,
    }


def list_admin_foods(db: Session, q: str | None = None, review_status: str | None = None, limit: int = 50):
    stmt = select(FoodItem).order_by(FoodItem.created_at.desc())
    if q:
        term = f'%{q.strip()}%'
        stmt = stmt.where(
            FoodItem.name_en.ilike(term) |
            FoodItem.name_ar.ilike(term) |
            FoodItem.vendor_name.ilike(term) |
            FoodItem.brand_name.ilike(term)
        )
    foods = db.scalars(stmt.limit(max(1, min(limit, 200)))).all()
    output = []
    for food in foods:
        review = db.get(FoodReview, food.id)
        if review_status and (review.review_status if review else 'PENDING') != review_status.upper():
            continue
        output.append({
            'id': food.id,
            'name_en': food.name_en,
            'name_ar': food.name_ar,
            'vendor_name': food.vendor_name,
            'brand_name': food.brand_name,
            'category': food.category,
            'barcode': food.barcode,
            'status': food.status,
            'nutrition': {
                'calories': food.nutrition.calories if food.nutrition else None,
                'protein_g': food.nutrition.protein_g if food.nutrition else None,
                'carbs_g': food.nutrition.carbs_g if food.nutrition else None,
                'fat_g': food.nutrition.fat_g if food.nutrition else None,
                'sodium_mg': food.nutrition.sodium_mg if food.nutrition else None,
            },
            'review': serialize_review(review),
        })
    return output


def parse_import_payload(format_: str, records: list[dict[str, Any]] | None, csv_text: str | None):
    format_ = format_.upper()
    if format_ == 'JSON':
        return records or []
    if format_ == 'CSV':
        if not csv_text:
            return []
        return [dict(row) for row in csv.DictReader(io.StringIO(csv_text))]
    raise ValueError('UNSUPPORTED_FORMAT')


def _num(value, field, errors):
    if value in (None, ''):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        errors.append(f'{field}: invalid number')
        return None
    if n < 0:
        errors.append(f'{field}: must be >= 0')
    return n


def validate_import(db: Session, rows: list[dict[str, Any]]):
    seen_ids, seen_barcodes = set(), set()
    result = []
    for index, raw in enumerate(rows):
        row = dict(raw)
        errors, warnings = [], []
        food_id = str(row.get('id') or '').strip()
        if not food_id:
            errors.append('id: required')
        elif food_id in seen_ids:
            errors.append('id: duplicate in payload')
        seen_ids.add(food_id)

        if not str(row.get('name_en') or row.get('name_ar') or '').strip():
            errors.append('name_en/name_ar: at least one required')

        serving_size = _num(row.get('serving_size'), 'serving_size', errors)
        calories = _num(row.get('calories'), 'calories', errors)
        protein = _num(row.get('protein_g'), 'protein_g', errors)
        carbs = _num(row.get('carbs_g'), 'carbs_g', errors)
        fat = _num(row.get('fat_g'), 'fat_g', errors)
        sodium = _num(row.get('sodium_mg'), 'sodium_mg', errors)

        barcode = str(row.get('barcode') or '').strip() or None
        if barcode:
            if barcode in seen_barcodes:
                errors.append('barcode: duplicate in payload')
            seen_barcodes.add(barcode)
            existing = db.scalar(select(FoodItem).where(FoodItem.barcode == barcode))
            if existing and existing.id != food_id:
                errors.append(f'barcode: already used by {existing.id}')

        existing_id = db.get(FoodItem, food_id) if food_id else None
        result.append({
            'index': index,
            'id': food_id or None,
            'operation': 'UPDATE' if existing_id else 'CREATE',
            'errors': errors,
            'warnings': warnings,
            'normalized': {
                'id': food_id,
                'name_en': (row.get('name_en') or None),
                'name_ar': (row.get('name_ar') or None),
                'food_type': row.get('food_type') or 'RESTAURANT',
                'brand_name': row.get('brand_name') or None,
                'vendor_name': row.get('vendor_name') or None,
                'category': row.get('category') or None,
                'serving_size': serving_size,
                'serving_unit': row.get('serving_unit') or None,
                'barcode': barcode,
                'price': _num(row.get('price'), 'price', errors),
                'currency': row.get('currency') or 'AED',
                'calories': calories,
                'protein_g': protein,
                'carbs_g': carbs,
                'fat_g': fat,
                'sodium_mg': sodium,
            }
        })
    return result


def import_foods(db: Session, rows: list[dict[str, Any]], dry_run: bool, actor: str):
    checked = validate_import(db, rows)
    created = updated = skipped = 0
    for item in checked:
        if item['errors']:
            skipped += 1
            continue
        if dry_run:
            continue
        n = item['normalized']
        food = db.get(FoodItem, n['id'])
        if food:
            updated += 1
        else:
            food = FoodItem(id=n['id'])
            db.add(food)
            created += 1
        for field in ['name_en','name_ar','food_type','brand_name','vendor_name','category','serving_size','serving_unit','barcode','price','currency']:
            setattr(food, field, n[field])
        nutrition = food.nutrition or FoodNutrition(food_id=food.id)
        if not food.nutrition:
            db.add(nutrition)
        for field in ['calories','protein_g','carbs_g','fat_g','sodium_mg']:
            setattr(nutrition, field, n[field])
    summary = {
        'dry_run': dry_run,
        'total': len(checked),
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'errors': sum(len(x['errors']) for x in checked),
        'warnings': sum(len(x['warnings']) for x in checked),
    }
    audit(db, 'FOOD_IMPORT_DRY_RUN' if dry_run else 'FOOD_IMPORT', 'BATCH', None, actor, summary)
    db.commit()
    return summary, checked



def _food_snapshot(food: FoodItem) -> dict[str, Any]:
    n=food.nutrition
    return {
        'id':food.id,
        'name_en':food.name_en,
        'name_ar':food.name_ar,
        'food_type':food.food_type,
        'brand_name':food.brand_name,
        'vendor_name':food.vendor_name,
        'category':food.category,
        'serving_size':food.serving_size,
        'serving_unit':food.serving_unit,
        'barcode':food.barcode,
        'price':food.price,
        'currency':food.currency,
        'availability_status':food.availability_status,
        'status':food.status,
        'nutrition':{
            'calories':n.calories if n else None,
            'protein_g':n.protein_g if n else None,
            'carbs_g':n.carbs_g if n else None,
            'fat_g':n.fat_g if n else None,
            'fiber_g':n.fiber_g if n else None,
            'sugar_g':n.sugar_g if n else None,
            'sodium_mg':n.sodium_mg if n else None,
        },
        'allergens':[
            {'code':x.allergen_code,'relationship_type':x.relationship_type}
            for x in food.allergens
        ],
    }


def edit_food(db: Session, food_id: str, changes: dict[str, Any], actor: str):
    food=db.get(FoodItem,food_id)
    if not food:
        raise ValueError('FOOD_NOT_FOUND')
    before=_food_snapshot(food)

    top_fields={
        'name_en','name_ar','food_type','brand_name','vendor_name','category',
        'serving_size','serving_unit','barcode','price','currency',
        'availability_status','status',
    }
    for key,value in changes.items():
        if key in top_fields:
            setattr(food,key,value)

    nutrition_changes=changes.get('nutrition')
    if nutrition_changes is not None:
        nutrition=food.nutrition
        if nutrition is None:
            nutrition=FoodNutrition(food_id=food.id)
            db.add(nutrition)
        allowed_nutrition={
            'calories','protein_g','carbs_g','fat_g','saturated_fat_g',
            'fiber_g','sugar_g','added_sugar_g','sodium_mg','cholesterol_mg',
        }
        for key,value in nutrition_changes.items():
            if key in allowed_nutrition:
                setattr(nutrition,key,value)

    allergens=changes.get('allergens')
    if allergens is not None:
        for row in list(food.allergens):
            db.delete(row)
        db.flush()
        seen=set()
        for item in allergens:
            code=str(item.get('code') or '').upper().strip()
            relationship=str(item.get('relationship_type') or 'CONTAINS').upper().strip()
            if not code or code in seen:
                continue
            seen.add(code)
            db.add(FoodAllergen(
                food_id=food.id,
                allergen_code=code,
                relationship_type=relationship,
            ))

    db.flush()
    db.refresh(food)
    after=_food_snapshot(food)
    audit(db,'FOOD_EDIT','FOOD',food.id,actor,{'before':before,'after':after})
    db.commit()
    return after


def merge_foods(db: Session, source_id: str, target_id: str, actor: str):
    if source_id==target_id:
        raise ValueError('SAME_FOOD')
    source=db.get(FoodItem,source_id)
    target=db.get(FoodItem,target_id)
    if not source or not target:
        raise ValueError('FOOD_NOT_FOUND')
    before_source=_food_snapshot(source)
    before_target=_food_snapshot(target)

    for field in [
        'name_en','name_ar','brand_name','vendor_name','category',
        'serving_size','serving_unit','price',
    ]:
        if getattr(target,field) in (None,'') and getattr(source,field) not in (None,''):
            setattr(target,field,getattr(source,field))

    if target.nutrition is None and source.nutrition is not None:
        target.nutrition=FoodNutrition(food_id=target.id)
        db.add(target.nutrition)
    if target.nutrition is not None and source.nutrition is not None:
        for field in [
            'calories','protein_g','carbs_g','fat_g','saturated_fat_g',
            'fiber_g','sugar_g','added_sugar_g','sodium_mg','cholesterol_mg',
        ]:
            if getattr(target.nutrition,field) is None and getattr(source.nutrition,field) is not None:
                setattr(target.nutrition,field,getattr(source.nutrition,field))

    target_allergens={x.allergen_code for x in target.allergens}
    for item in source.allergens:
        if item.allergen_code not in target_allergens:
            db.add(FoodAllergen(
                food_id=target.id,
                allergen_code=item.allergen_code,
                relationship_type=item.relationship_type,
            ))
            target_allergens.add(item.allergen_code)

    existing_sources={
        (x.source_type,x.source_name,x.source_reference)
        for x in target.sources
    }
    for item in source.sources:
        key=(item.source_type,item.source_name,item.source_reference)
        if key not in existing_sources:
            db.add(FoodDataSource(
                food_id=target.id,
                source_type=item.source_type,
                source_name=item.source_name,
                source_reference=item.source_reference,
                source_market=item.source_market,
                confidence_level=item.confidence_level,
                verified_at=item.verified_at,
            ))
            existing_sources.add(key)

    for model in [
        FoodLog, RecommendationFeedback, WeeklyPlanItem, FavoriteMeal,
        RecommendationExclusionLog, RecommendationDecisionLog,
    ]:
        db.execute(
            update(model)
            .where(model.food_id==source_id)
            .values(food_id=target_id)
        )

    source.status='MERGED'
    source.availability_status='UNAVAILABLE'
    source.barcode=None

    db.flush()
    db.refresh(target)
    db.refresh(source)
    details={
        'source_id':source_id,
        'target_id':target_id,
        'before_source':before_source,
        'before_target':before_target,
        'after_source':_food_snapshot(source),
        'after_target':_food_snapshot(target),
    }
    audit(db,'FOOD_MERGE','FOOD',target_id,actor,details)
    db.commit()
    return {
        'source_id':source_id,
        'target_id':target_id,
        'source_status':source.status,
        'target':_food_snapshot(target),
    }
