from typing import Any

from sqlalchemy.orm import Session

from app.services.catalog import query_foods, serialize_food


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_vision_review(db: Session, vision_result: dict[str, Any] | None) -> dict[str, Any]:
    result=vision_result or {}
    output=[]
    flat=[]
    seen=set()

    for index,raw in enumerate(result.get('items') or []):
        if not isinstance(raw,dict):
            continue
        name_ar=str(raw.get('name_ar') or '').strip()
        name=str(raw.get('name') or '').strip()
        query=name_ar or name
        candidates=query_foods(db,q=query,limit=6) if query else []
        serialized=[serialize_food(x) for x in candidates]

        for food in serialized:
            if food['food_id'] not in seen:
                seen.add(food['food_id'])
                flat.append(food)

        confidence=_float(raw.get('confidence'),0.0)
        output.append({
            'index':index,
            'raw_text':query or f'item-{index+1}',
            'query_text':query,
            'estimated_quantity':max(0.1,_float(raw.get('estimated_quantity'),1.0)),
            'estimated_unit':str(raw.get('estimated_unit') or 'SERVING').upper(),
            'confidence_score':round(max(0.0,min(1.0,confidence)),3),
            'confidence':'HIGH' if confidence>=0.8 else 'MEDIUM' if confidence>=0.55 else 'LOW',
            'requires_confirmation':confidence<0.75,
            'editable':True,
            'vision_estimate':{
                'calories':raw.get('estimated_calories'),
                'protein_g':raw.get('estimated_protein_g'),
                'carbs_g':raw.get('estimated_carbs_g'),
                'fat_g':raw.get('estimated_fat_g'),
            },
            'candidates':serialized,
        })

    overall=_float(result.get('overall_confidence'),0.0)
    return {
        'description_ar':result.get('description_ar'),
        'preview_required':True,
        'auto_saved':False,
        'items':output,
        'candidates':flat,
        'overall_confidence':round(max(0.0,min(1.0,overall)),3),
        'needs_review':True,
        'note':'Image analysis is an estimate. Review every detected item, match and portion before saving.',
    }
