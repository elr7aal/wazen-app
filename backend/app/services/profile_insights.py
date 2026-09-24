from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.db_models import User, FoodLog, RecommendationFeedback
from app.services.persistence import ensure_profile

def profile_insights(db: Session, user: User) -> dict:
    p=ensure_profile(db,user)
    logs=db.scalars(select(FoodLog).where(FoodLog.user_id==user.id, FoodLog.food_id.is_not(None))).all()
    feedback=db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.user_id==user.id)).all()
    repeats=Counter(x.food_id for x in logs if x.food_id)
    accepted=Counter(f.food_id for f in feedback if f.action in {'SAVE','ACCEPT','ORDER'})
    rejected=Counter(f.food_id for f in feedback if f.action=='REJECT')
    learned_positive=[{'food_id':food_id,'signal_count':count,'signal':'REPEATED_CHOICE'} for food_id,count in repeats.most_common(5) if count>=2]
    learned_positive += [{'food_id':food_id,'signal_count':count,'signal':'POSITIVE_FEEDBACK'} for food_id,count in accepted.most_common(5) if food_id not in {x['food_id'] for x in learned_positive}]
    learned_negative=[{'food_id':food_id,'signal_count':count,'signal':'REJECTED'} for food_id,count in rejected.most_common(5)]
    return {'hard_exclusions': p.severe_allergens(),'stated_preferences': p.food_preferences(),'stated_dislikes': p.disliked_foods(),'learned_positive': learned_positive[:5],'learned_negative': learned_negative[:5],'explanation_ar': ['الحساسية الشديدة تعمل كاستبعاد سلامة ولا يمكن للتفضيل تجاوزها.','الأشياء التي اخترتها كمفضلة ترفع ترتيب النتائج المشابهة بشكل محدود.','الأشياء التي لا تفضلها تنخفض في الترتيب لكنها لا تختفي تلقائيًا.','الحفظ والتكرار والقبول تعطي إشارة إيجابية تدريجية، والرفض يقلل الظهور مستقبلًا.','السعرات والبروتين والقيود الصحية تبقى عوامل مستقلة داخل Wazen Match.']}
