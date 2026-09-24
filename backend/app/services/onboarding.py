from datetime import date
from app.models.schemas import OnboardingCompleteRequest

ACTIVITY_FACTORS = {
    'SEDENTARY': 1.20,
    'LIGHT': 1.375,
    'MODERATE': 1.55,
    'ACTIVE': 1.725,
    'VERY_ACTIVE': 1.90,
}

def age_years(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def calculate_targets(req: OnboardingCompleteRequest) -> dict:
    age = age_years(req.date_of_birth)
    # Mifflin-St Jeor estimate. Used as a configurable starting estimate, not medical treatment.
    sex_constant = 5 if req.gender == 'MALE' else -161
    bmr = 10 * req.weight_kg + 6.25 * req.height_cm - 5 * age + sex_constant
    tdee = bmr * ACTIVITY_FACTORS[req.activity_level]

    if req.goal_type == 'LOSE':
        calories = tdee * 0.85
    elif req.goal_type == 'GAIN':
        calories = tdee * 1.10
    else:
        calories = tdee

    # Guardrails for generic consumer onboarding.
    calories = max(1200.0, min(4500.0, calories))

    target_weight = req.target_weight_kg or req.weight_kg
    protein_per_kg = 1.6 if req.goal_type in {'LOSE','GAIN'} else 1.4
    protein = max(60.0, min(250.0, target_weight * protein_per_kg))
    fat = max(40.0, calories * 0.28 / 9)
    carbs = max(50.0, (calories - protein * 4 - fat * 9) / 4)

    return {
        'age': age,
        'estimated_bmr': round(bmr),
        'estimated_tdee': round(tdee),
        'target_calories': round(calories),
        'target_protein_g': round(protein),
        'target_carbs_g': round(carbs),
        'target_fat_g': round(fat),
        'sodium_max_mg': 2300,
        'method': 'MIFFLIN_ST_JEOR_STARTING_ESTIMATE',
        'note': 'Starting estimate for general wellness. User can edit targets; clinician-defined limits should override generic targets.'
    }
