from datetime import datetime, date, timezone
from uuid import uuid4
from sqlalchemy import String, Float, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


def uid() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default='ar')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    profile: Mapped['UserProfile | None'] = relationship(back_populates='user', uselist=False, cascade='all, delete-orphan')
    logs: Mapped[list['FoodLog']] = relationship(back_populates='user', cascade='all, delete-orphan')


class UserProfile(Base):
    __tablename__ = 'user_profiles'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), unique=True, index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_level: Mapped[str] = mapped_column(String(32), default='LIGHT')
    goal_type: Mapped[str] = mapped_column(String(32), default='MAINTAIN')
    daily_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_calories: Mapped[float] = mapped_column(Float, default=2000)
    target_protein_g: Mapped[float] = mapped_column(Float, default=100)
    target_carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_max_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    severe_allergens_csv: Mapped[str] = mapped_column(Text, default='')
    food_preferences_csv: Mapped[str] = mapped_column(Text, default='')
    disliked_foods_csv: Mapped[str] = mapped_column(Text, default='')
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship(back_populates='profile')

    def severe_allergens(self) -> list[str]:
        return [x for x in self.severe_allergens_csv.split('|') if x]

    def food_preferences(self) -> list[str]:
        return [x for x in self.food_preferences_csv.split('|') if x]

    def disliked_foods(self) -> list[str]:
        return [x for x in self.disliked_foods_csv.split('|') if x]


class FoodItem(Base):
    __tablename__ = 'food_items'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_en: Mapped[str | None] = mapped_column(String(250), nullable=True, index=True)
    name_ar: Mapped[str | None] = mapped_column(String(250), nullable=True, index=True)
    food_type: Mapped[str] = mapped_column(String(30), index=True)
    brand_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    vendor_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    serving_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    serving_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default='AED')
    availability_status: Mapped[str] = mapped_column(String(30), default='AVAILABLE')
    status: Mapped[str] = mapped_column(String(30), default='ACTIVE')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    nutrition: Mapped['FoodNutrition | None'] = relationship(back_populates='food', uselist=False, cascade='all, delete-orphan')
    allergens: Mapped[list['FoodAllergen']] = relationship(back_populates='food', cascade='all, delete-orphan')
    sources: Mapped[list['FoodDataSource']] = relationship(back_populates='food', cascade='all, delete-orphan')


class FoodNutrition(Base):
    __tablename__ = 'food_nutrition'
    food_id: Mapped[str] = mapped_column(ForeignKey('food_items.id', ondelete='CASCADE'), primary_key=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    saturated_fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sugar_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    added_sugar_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    cholesterol_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    food: Mapped[FoodItem] = relationship(back_populates='nutrition')


class FoodAllergen(Base):
    __tablename__ = 'food_allergens'
    __table_args__ = (UniqueConstraint('food_id', 'allergen_code', name='uq_food_allergen'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    food_id: Mapped[str] = mapped_column(ForeignKey('food_items.id', ondelete='CASCADE'), index=True)
    allergen_code: Mapped[str] = mapped_column(String(40), index=True)
    relationship_type: Mapped[str] = mapped_column(String(30), default='CONTAINS')
    food: Mapped[FoodItem] = relationship(back_populates='allergens')


class FoodDataSource(Base):
    __tablename__ = 'food_data_sources'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    food_id: Mapped[str] = mapped_column(ForeignKey('food_items.id', ondelete='CASCADE'), index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_market: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    food: Mapped[FoodItem] = relationship(back_populates='sources')


class FoodModifier(Base):
    __tablename__ = 'food_modifiers'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vendor_name: Mapped[str] = mapped_column(String(200), index=True)
    menu_item_name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    modifier_group: Mapped[str] = mapped_column(String(50))
    name_en: Mapped[str] = mapped_column(String(250))
    name_ar: Mapped[str | None] = mapped_column(String(250), nullable=True)
    action: Mapped[str] = mapped_column(String(30))
    calorie_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_delta_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_delta_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_delta_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sugar_delta_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_delta_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(20), nullable=True)


class FoodLog(Base):
    __tablename__ = 'food_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    food_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    food_name: Mapped[str] = mapped_column(String(255))
    meal_type: Mapped[str] = mapped_column(String(32))
    entry_method: Mapped[str] = mapped_column(String(32), default='MANUAL')
    calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    sodium_mg: Mapped[float] = mapped_column(Float, default=0)
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
    user: Mapped[User] = relationship(back_populates='logs')


class RecommendationFeedback(Base):
    __tablename__ = 'recommendation_feedback'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    food_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(24), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)


class FoodReview(Base):
    __tablename__ = 'food_reviews'
    food_id: Mapped[str] = mapped_column(ForeignKey('food_items.id', ondelete='CASCADE'), primary_key=True)
    review_status: Mapped[str] = mapped_column(String(24), default='PENDING', index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AdminAuditLog(Base):
    __tablename__ = 'admin_audit_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    action: Mapped[str] = mapped_column(String(50), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(120), default='admin')
    details_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)


class WeeklyPlanItem(Base):
    __tablename__ = 'weekly_plan_items'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(32), index=True)
    food_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    food_name: Mapped[str] = mapped_column(String(255))
    calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default='AED')
    status: Mapped[str] = mapped_column(String(24), default='PLANNED')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class WeightHistory(Base):
    __tablename__ = 'weight_history'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    rotated_from_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)


class GoalHistory(Base):
    __tablename__ = 'goal_history'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    reason: Mapped[str] = mapped_column(String(40), default='PROFILE_UPDATE', index=True)
    snapshot_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)


class UserPreferenceSetting(Base):
    __tablename__ = 'user_preference_settings'
    __table_args__ = (UniqueConstraint('user_id', 'target_type', 'target_value', name='uq_user_preference_target'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    target_type: Mapped[str] = mapped_column(String(20), index=True)
    target_value: Mapped[str] = mapped_column(String(120), index=True)
    level: Mapped[str] = mapped_column(String(20), default='NEUTRAL', index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class HealthLimit(Base):
    __tablename__ = 'health_limits'
    __table_args__ = (UniqueConstraint('user_id', 'nutrient_code', 'limit_type', name='uq_user_health_limit'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    nutrient_code: Mapped[str] = mapped_column(String(40), index=True)
    limit_type: Mapped[str] = mapped_column(String(12), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(12), default='SOFT', index=True)
    source_type: Mapped[str] = mapped_column(String(20), default='USER', index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class FavoriteMeal(Base):
    __tablename__ = 'favorite_meals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    food_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    food_name: Mapped[str] = mapped_column(String(255))
    default_meal_type: Mapped[str] = mapped_column(String(32), default='SNACK')
    calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    sodium_mg: Mapped[float] = mapped_column(Float, default=0)
    source_log_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
