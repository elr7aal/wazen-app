import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import RecommendationExclusionLog


def record_exclusions(db: Session, user_id: str, excluded: list[dict], context: dict) -> int:
    count=0
    for item in excluded:
        food_id=str(item.get('food_id') or '').strip()
        reason=str(item.get('reason') or '').strip()
        if not food_id or not reason:
            continue
        details=item.get('details') or []
        row=RecommendationExclusionLog(
            user_id=user_id,
            food_id=food_id,
            reason=reason,
            details_json=json.dumps(details,ensure_ascii=False,default=str),
            context_json=json.dumps(context,ensure_ascii=False,default=str),
        )
        db.add(row)
        count+=1
    if count:
        db.commit()
    return count


def list_exclusions(db: Session, user_id: str, limit: int=100, reason: str|None=None):
    stmt=select(RecommendationExclusionLog).where(
        RecommendationExclusionLog.user_id==user_id
    )
    if reason:
        stmt=stmt.where(RecommendationExclusionLog.reason==reason)
    rows=db.scalars(
        stmt.order_by(RecommendationExclusionLog.created_at.desc())
        .limit(max(1,min(limit,500)))
    ).all()
    output=[]
    for x in rows:
        try:
            details=json.loads(x.details_json)
        except Exception:
            details=[]
        try:
            context=json.loads(x.context_json)
        except Exception:
            context={}
        output.append({
            'id':x.id,
            'food_id':x.food_id,
            'reason':x.reason,
            'details':details,
            'context':context,
            'created_at':x.created_at.isoformat(),
        })
    return output
