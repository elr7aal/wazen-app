import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.catalog import query_foods, serialize_food


ARABIC_FRACTIONS = {
    'نص': 0.5,
    'نصف': 0.5,
    'ربع': 0.25,
}
UNIT_ALIASES = {
    'كوب': 'CUP',
    'كاسة': 'CUP',
    'كاس': 'CUP',
    'علبة': 'CAN',
    'حبة': 'ITEM',
    'حبه': 'ITEM',
    'طبق': 'PLATE',
    'ساندويتش': 'ITEM',
    'سندويتش': 'ITEM',
    'جرام': 'G',
    'غرام': 'G',
    'g': 'G',
    'ml': 'ML',
    'مل': 'ML',
}

def _split_items(text: str) -> list[str]:
    clean=' '.join((text or '').strip().split())
    if not clean:
        return []
    parts=re.split(r'\s+(?:and\s+|و\s+|و(?=[\u0600-\u06FF]))|[,،;+]',clean,flags=re.IGNORECASE)
    return [x.strip() for x in parts if x and x.strip()]


def _portion(segment: str) -> tuple[float,str,str]:
    lower=segment.lower()
    quantity=1.0
    unit='SERVING'
    cleaned=segment

    m=re.search(r'(?<!\w)(\d+(?:\.\d+)?)\s*(كوب|كاسة|كاس|علبة|حبة|حبه|طبق|ساندويتش|سندويتش|جرام|غرام|g|ml|مل)?\b',lower)
    if m:
        quantity=float(m.group(1))
        if m.group(2):
            unit=UNIT_ALIASES.get(m.group(2),'SERVING')
        cleaned=(segment[:m.start()]+segment[m.end():]).strip()
    else:
        for word,value in ARABIC_FRACTIONS.items():
            fm=re.search(rf'(?<!\w){word}(?!\w)',lower)
            if fm:
                quantity=value
                cleaned=(segment[:fm.start()]+segment[fm.end():]).strip()
                break
        for word,normalized in UNIT_ALIASES.items():
            um=re.search(rf'(?<!\w){re.escape(word)}(?!\w)',cleaned.lower())
            if um:
                unit=normalized
                cleaned=(cleaned[:um.start()]+cleaned[um.end():]).strip()
                break

    cleaned=' '.join(cleaned.split())
    return quantity,unit,cleaned or segment.strip()


def parse_natural_food_text(db: Session,text: str,limit_per_item: int=4) -> dict[str,Any]:
    segments=_split_items(text)
    items=[]
    flat=[]
    seen=set()
    for index,segment in enumerate(segments):
        quantity,unit,query=_portion(segment)
        candidates=query_foods(db,q=query,limit=limit_per_item)
        serialized=[serialize_food(x) for x in candidates]
        for food in serialized:
            if food['food_id'] not in seen:
                seen.add(food['food_id'])
                flat.append(food)

        confidence='UNKNOWN'
        if serialized:
            q=query.lower()
            top=serialized[0]
            names=' '.join([
                str(top.get('name') or ''),
                str(top.get('name_ar') or ''),
                str(top.get('category') or ''),
            ]).lower()
            confidence='HIGH' if q and q in names else 'MEDIUM'

        items.append({
            'index':index,
            'raw_text':segment,
            'query_text':query,
            'estimated_quantity':quantity,
            'estimated_unit':unit,
            'confidence':confidence,
            'editable':True,
            'candidates':serialized,
        })

    return {
        'input':text,
        'preview_required':True,
        'auto_saved':False,
        'items':items,
        'candidates':flat,
        'confidence':'MIXED' if len(items)>1 else (items[0]['confidence'] if items else 'UNKNOWN'),
        'status':'MATCHES_FOUND' if any(x['candidates'] for x in items) else 'REVIEW_REQUIRED',
        'note':'Review every detected item, candidate and portion before saving. WAZEN does not auto-log text parsing.',
    }
