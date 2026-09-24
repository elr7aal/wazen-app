from typing import Optional, List, Literal, Dict
from datetime import date
from pydantic import BaseModel, Field


class DailyStateRequest(BaseModel):
    target_calories: float = Field(gt=0)
    consumed_calories: float = Field(ge=0)
    activity_credit: float = Field(default=0, ge=0)
    target_protein_g: float = Field(default=0, ge=0)
    consumed_protein_g: float = Field(default=0, ge=0)
    target_carbs_g: Optional[float] = Field(default=None, ge=0)
    consumed_carbs_g: Optional[float] = Field(default=None, ge=0)
    target_fat_g: Optional[float] = Field(default=None, ge=0)
    consumed_fat_g: Optional[float] = Field(default=None, ge=0)
    sodium_max_mg: Optional[float] = Field(default=None, ge=0)
    consumed_sodium_mg: Optional[float] = Field(default=None, ge=0)


class DailyState(BaseModel):
    remaining_calories: float
    protein_gap_g: float
    carbs_remaining_g: Optional[float] = None
    fat_remaining_g: Optional[float] = None
    sodium_remaining_mg: Optional[float] = None


class RecommendationRequest(BaseModel):
    daily_state: DailyStateRequest
    vendor: Optional[str] = None
    category: Optional[str] = None
    max_calories: Optional[float] = None
    min_protein_g: Optional[float] = None
    budget_max: Optional[float] = None
    severe_allergens: List[str] = []
    allow_modifications: bool = True
    preferred_terms: List[str] = []
    disliked_terms: List[str] = []
    behavior_scores: Dict[str, float] = {}
    preference_levels: Dict[str, str] = {}
    food_preference_levels: Dict[str, str] = {}
    never_show_terms: List[str] = []
    never_show_food_ids: List[str] = []


class ModificationContext(BaseModel):
    included_components: List[str] = []


class MakeItFitRequest(BaseModel):
    food_id: str
    daily_state: DailyStateRequest
    included_components: List[Literal[
        "REGULAR_PEPSI_453ML",
        "MEDIUM_FRIES",
        "LARGE_FRIES",
        "DYNAMITE_SAUCE_DIP",
        "RANCH_SAUCE_DIP"
    ]] = []


class RebalanceRequest(BaseModel):
    daily_state: DailyStateRequest
    added_calories: float = Field(ge=0)
    added_protein_g: float = Field(default=0, ge=0)
    added_carbs_g: float = Field(default=0, ge=0)
    added_fat_g: float = Field(default=0, ge=0)
    added_sodium_mg: float = Field(default=0, ge=0)

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    first_name: Optional[str] = None
    language: str = 'ar'


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Literal['MALE','FEMALE']] = None
    height_cm: Optional[float] = Field(default=None, gt=0)
    weight_kg: Optional[float] = Field(default=None, gt=0)
    target_weight_kg: Optional[float] = Field(default=None, gt=0)
    activity_level: Optional[str] = None
    goal_type: Optional[str] = None
    daily_budget: Optional[float] = Field(default=None, ge=0)
    target_calories: Optional[float] = Field(default=None, gt=0)
    target_protein_g: Optional[float] = Field(default=None, ge=0)
    target_carbs_g: Optional[float] = Field(default=None, ge=0)
    target_fat_g: Optional[float] = Field(default=None, ge=0)
    sodium_max_mg: Optional[float] = Field(default=None, ge=0)
    severe_allergens: Optional[List[str]] = None
    food_preferences: Optional[List[str]] = None
    disliked_foods: Optional[List[str]] = None


class FoodLogCreateRequest(BaseModel):
    food_id: Optional[str] = None
    food_name: str
    meal_type: Literal['BREAKFAST','LUNCH','DINNER','SNACK']
    entry_method: str = 'MANUAL'
    calories: float = Field(ge=0)
    protein_g: float = Field(default=0, ge=0)
    carbs_g: float = Field(default=0, ge=0)
    fat_g: float = Field(default=0, ge=0)
    sodium_mg: float = Field(default=0, ge=0)


class UserRecommendationRequest(BaseModel):
    vendor: Optional[str] = None
    category: Optional[str] = None
    max_calories: Optional[float] = Field(default=None, ge=0)
    budget_max: Optional[float] = Field(default=None, ge=0)
    allow_modifications: bool = True


class CatalogFoodLogRequest(BaseModel):
    food_id: str
    meal_type: Literal['BREAKFAST','LUNCH','DINNER','SNACK']
    quantity: float = Field(default=1.0, gt=0)
    entry_method: str = 'CATALOG'


class GoldenFlowRequest(BaseModel):
    craving_text: str
    meal_type: Literal['BREAKFAST','LUNCH','DINNER','SNACK'] = 'DINNER'
    auto_log_food_id: Optional[str] = None
    quantity: float = Field(default=1.0, gt=0)
    allow_modifications: bool = True


class ModifiedCatalogFoodLogRequest(BaseModel):
    food_id: str
    meal_type: Literal['BREAKFAST','LUNCH','DINNER','SNACK'] = 'DINNER'
    quantity: float = Field(default=1.0, gt=0)
    included_components: List[Literal[
        "REGULAR_PEPSI_453ML",
        "MEDIUM_FRIES",
        "LARGE_FRIES",
        "DYNAMITE_SAUCE_DIP",
        "RANCH_SAUCE_DIP"
    ]] = []


class FoodLogUpdateRequest(BaseModel):
    meal_type: Optional[Literal['BREAKFAST','LUNCH','DINNER','SNACK']] = None
    calories: Optional[float] = Field(default=None, ge=0)
    protein_g: Optional[float] = Field(default=None, ge=0)
    carbs_g: Optional[float] = Field(default=None, ge=0)
    fat_g: Optional[float] = Field(default=None, ge=0)
    sodium_mg: Optional[float] = Field(default=None, ge=0)


class TextFoodParseRequest(BaseModel):
    text: str = Field(min_length=1)
    meal_type: Literal['BREAKFAST','LUNCH','DINNER','SNACK'] = 'SNACK'

class ImageFoodAnalyzeRequest(BaseModel):
    image_base64: str = Field(min_length=8)
    user_caption: Optional[str] = None
    meal_type: Literal['BREAKFAST','LUNCH','DINNER','SNACK'] = 'SNACK'


class OnboardingCompleteRequest(BaseModel):
    first_name: Optional[str] = None
    date_of_birth: date
    gender: Literal['MALE','FEMALE']
    height_cm: float = Field(ge=120, le=230)
    weight_kg: float = Field(ge=35, le=300)
    target_weight_kg: Optional[float] = Field(default=None, ge=35, le=300)
    goal_type: Literal['LOSE','MAINTAIN','GAIN']
    activity_level: Literal['SEDENTARY','LIGHT','MODERATE','ACTIVE','VERY_ACTIVE']
    daily_budget: Optional[float] = Field(default=None, ge=0)
    severe_allergens: List[str] = []
    food_preferences: List[str] = []
    disliked_foods: List[str] = []


class RecommendationFeedbackRequest(BaseModel):
    food_id: str
    action: Literal['SAVE','ACCEPT','REJECT','ORDER']


class PlanRecalculateRequest(BaseModel):
    weight_kg: Optional[float] = Field(default=None, ge=35, le=300)
    target_weight_kg: Optional[float] = Field(default=None, ge=35, le=300)
    goal_type: Optional[Literal['LOSE','MAINTAIN','GAIN']] = None
    activity_level: Optional[Literal['SEDENTARY','LIGHT','MODERATE','ACTIVE','VERY_ACTIVE']] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20)
    all_sessions: bool = False


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8)


class PreferenceSettingRequest(BaseModel):
    target_type: Literal['TERM','FOOD']
    target_value: str = Field(min_length=1, max_length=120)
    level: Literal['LOVE','LIKE','NEUTRAL','DISLIKE','NEVER_SHOW']


class HealthLimitRequest(BaseModel):
    nutrient_code: Literal['CALORIES','PROTEIN_G','CARBS_G','FAT_G','SATURATED_FAT_G','SUGAR_G','SODIUM_MG']
    limit_type: Literal['MAX','MIN']
    value: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=20)
    severity: Literal['HARD','SOFT'] = 'SOFT'
    source_type: Literal['USER','CLINICIAN'] = 'USER'
    note: Optional[str] = Field(default=None, max_length=500)
    active: bool = True
