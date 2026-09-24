from app.models.schemas import RebalanceRequest, DailyStateRequest
from app.services.daily_state import calculate_daily_state


def rebalance_day(req: RebalanceRequest):
    d = req.daily_state
    updated = DailyStateRequest(
        target_calories=d.target_calories,
        consumed_calories=d.consumed_calories + req.added_calories,
        activity_credit=d.activity_credit,
        target_protein_g=d.target_protein_g,
        consumed_protein_g=d.consumed_protein_g + req.added_protein_g,
        target_carbs_g=d.target_carbs_g,
        consumed_carbs_g=None if d.consumed_carbs_g is None else d.consumed_carbs_g + req.added_carbs_g,
        target_fat_g=d.target_fat_g,
        consumed_fat_g=None if d.consumed_fat_g is None else d.consumed_fat_g + req.added_fat_g,
        sodium_max_mg=d.sodium_max_mg,
        consumed_sodium_mg=None if d.consumed_sodium_mg is None else d.consumed_sodium_mg + req.added_sodium_mg,
    )
    state = calculate_daily_state(updated)
    raw_balance = d.target_calories - (d.consumed_calories + req.added_calories) + d.activity_credit

    if raw_balance < 0:
        message = f"Your choice is about {abs(raw_balance):.0f} kcal above the current plan. Wazen can keep the choice and make later suggestions lighter."
    else:
        message = f"Meal recorded. About {raw_balance:.0f} kcal remain in the current plan."

    return {"updated_state": state.model_dump(), "message": message, "user_choice_preserved": True}
