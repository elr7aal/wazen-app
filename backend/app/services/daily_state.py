from app.models.schemas import DailyStateRequest, DailyState


def calculate_daily_state(req: DailyStateRequest) -> DailyState:
    remaining_calories = max(0.0, req.target_calories - req.consumed_calories + req.activity_credit)
    protein_gap = max(0.0, req.target_protein_g - req.consumed_protein_g)

    carbs_remaining = None
    if req.target_carbs_g is not None and req.consumed_carbs_g is not None:
        carbs_remaining = max(0.0, req.target_carbs_g - req.consumed_carbs_g)

    fat_remaining = None
    if req.target_fat_g is not None and req.consumed_fat_g is not None:
        fat_remaining = max(0.0, req.target_fat_g - req.consumed_fat_g)

    sodium_remaining = None
    if req.sodium_max_mg is not None and req.consumed_sodium_mg is not None:
        sodium_remaining = max(0.0, req.sodium_max_mg - req.consumed_sodium_mg)

    return DailyState(
        remaining_calories=round(remaining_calories, 1),
        protein_gap_g=round(protein_gap, 1),
        carbs_remaining_g=None if carbs_remaining is None else round(carbs_remaining, 1),
        fat_remaining_g=None if fat_remaining is None else round(fat_remaining, 1),
        sodium_remaining_mg=None if sodium_remaining is None else round(sodium_remaining, 1),
    )
