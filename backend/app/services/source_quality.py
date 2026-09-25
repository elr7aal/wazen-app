from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.db_models import FoodItem


FRESH_DAYS=180
AGING_DAYS=365
CONFIDENCE_RANK={
    'VERIFIED':5,
    'HIGH':4,
    'MEDIUM':3,
    'LOW':2,
    'ESTIMATED':1,
}


def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def primary_source(item: FoodItem):
    if not item.sources:
        return None
    return max(
        item.sources,
        key=lambda s: (
            CONFIDENCE_RANK.get((s.confidence_level or '').upper(),0),
            s.verified_at or datetime.min,
        ),
    )


def source_freshness(source, now: datetime | None=None):
    if source is None or source.verified_at is None:
        return {'status':'UNKNOWN','age_days':None}
    now=now or utcnow_naive()
    age=max(0,(now.date()-source.verified_at.date()).days)
    if age<=FRESH_DAYS:
        status='FRESH'
    elif age<=AGING_DAYS:
        status='AGING'
    else:
        status='STALE'
    return {'status':status,'age_days':age}


def catalog_quality_report(db: Session, limit: int=100):
    foods=db.scalars(
        select(FoodItem)
        .options(
            selectinload(FoodItem.nutrition),
            selectinload(FoodItem.sources),
        )
        .where(FoodItem.status=='ACTIVE')
        .order_by(FoodItem.id)
    ).all()

    summary={
        'active_foods':len(foods),
        'fresh':0,
        'aging':0,
        'stale':0,
        'unknown_verification':0,
        'missing_source':0,
        'missing_core_nutrition':0,
        'missing_sodium':0,
    }
    issues=[]
    issue_count=0

    for food in foods:
        source=primary_source(food)
        freshness=source_freshness(source)
        status=freshness['status']
        if status=='FRESH':
            summary['fresh']+=1
        elif status=='AGING':
            summary['aging']+=1
        elif status=='STALE':
            summary['stale']+=1
        else:
            summary['unknown_verification']+=1

        flags=[]
        if source is None:
            summary['missing_source']+=1
            flags.append('MISSING_SOURCE')
        elif source.verified_at is None:
            flags.append('MISSING_VERIFICATION_DATE')
        elif status=='AGING':
            flags.append('SOURCE_AGING')
        elif status=='STALE':
            flags.append('SOURCE_STALE')

        n=food.nutrition
        core_missing=(
            n is None or
            any(getattr(n,field,None) is None for field in ['calories','protein_g','carbs_g','fat_g'])
        )
        if core_missing:
            summary['missing_core_nutrition']+=1
            flags.append('MISSING_CORE_NUTRITION')
        if n is None or n.sodium_mg is None:
            summary['missing_sodium']+=1
            flags.append('MISSING_SODIUM')

        if flags:
            issue_count+=1
        if flags and len(issues)<max(1,min(limit,500)):
            issues.append({
                'food_id':food.id,
                'name':food.name_en or food.name_ar,
                'vendor':food.vendor_name,
                'flags':flags,
                'source_name':source.source_name if source else None,
                'source_confidence':source.confidence_level if source else None,
                'source_verified_at':source.verified_at.isoformat() if source and source.verified_at else None,
                'source_freshness':status,
                'source_age_days':freshness['age_days'],
            })

    return {'summary':summary,'issues':issues,'issue_count':issue_count,'returned_issues':len(issues)}
