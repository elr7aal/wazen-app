import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import RecommendationExclusionLog, RecommendationDecisionLog


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



def record_decisions(db: Session, user_id: str, results: list[dict], context: dict, engine_version: str='v1') -> int:
    count=0
    for index,item in enumerate(results, start=1):
        food_id=str(item.get('food_id') or '').strip()
        if not food_id:
            continue
        scores=item.get('scores') or {}
        row=RecommendationDecisionLog(
            user_id=user_id,
            food_id=food_id,
            rank_position=index,
            decision=str(item.get('decision') or 'UNKNOWN'),
            score_wazen=float(scores.get('wazen') or 0.0),
            scores_json=json.dumps(scores,ensure_ascii=False,default=str),
            reasons_json=json.dumps(item.get('reasons') or [],ensure_ascii=False,default=str),
            warnings_json=json.dumps(item.get('warnings') or [],ensure_ascii=False,default=str),
            context_json=json.dumps(context,ensure_ascii=False,default=str),
            engine_version=engine_version,
        )
        db.add(row)
        count+=1
    if count:
        db.commit()
    return count


def list_decisions(db: Session, user_id: str, limit: int=100, food_id: str|None=None):
    stmt=select(RecommendationDecisionLog).where(
        RecommendationDecisionLog.user_id==user_id
    )
    if food_id:
        stmt=stmt.where(RecommendationDecisionLog.food_id==food_id)
    rows=db.scalars(
        stmt.order_by(RecommendationDecisionLog.created_at.desc(),RecommendationDecisionLog.rank_position)
        .limit(max(1,min(limit,500)))
    ).all()
    output=[]
    for x in rows:
        def parse(raw,default):
            try:return json.loads(raw)
            except Exception:return default
        output.append({
            'id':x.id,
            'food_id':x.food_id,
            'rank_position':x.rank_position,
            'decision':x.decision,
            'score_wazen':x.score_wazen,
            'scores':parse(x.scores_json,{}),
            'reasons':parse(x.reasons_json,[]),
            'warnings':parse(x.warnings_json,[]),
            'context':parse(x.context_json,{}),
            'engine_version':x.engine_version,
            'created_at':x.created_at.isoformat(),
        })
    return output
