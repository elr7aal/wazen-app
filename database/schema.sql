CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email VARCHAR(320) UNIQUE NOT NULL, password_hash TEXT NOT NULL,
  first_name VARCHAR(120), language VARCHAR(10) DEFAULT 'ar', active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date_of_birth DATE, gender VARCHAR(32), height_cm NUMERIC(6,2), weight_kg NUMERIC(6,2), target_weight_kg NUMERIC(6,2),
  activity_level VARCHAR(32) DEFAULT 'LIGHT', goal_type VARCHAR(32) DEFAULT 'MAINTAIN', daily_budget NUMERIC(10,2),
  target_calories NUMERIC(10,2) DEFAULT 2000, target_protein_g NUMERIC(10,2) DEFAULT 100, target_carbs_g NUMERIC(10,2),
  target_fat_g NUMERIC(10,2), sodium_max_mg NUMERIC(10,2), severe_allergens_csv TEXT DEFAULT ''
);
CREATE TABLE food_items (
  id VARCHAR(64) PRIMARY KEY, name_en VARCHAR(250), name_ar VARCHAR(250), food_type VARCHAR(30) NOT NULL,
  brand_name VARCHAR(200), vendor_name VARCHAR(200), category VARCHAR(60), serving_size NUMERIC(10,3), serving_unit VARCHAR(30),
  barcode VARCHAR(100) UNIQUE, price NUMERIC(10,2), currency VARCHAR(8) DEFAULT 'AED', availability_status VARCHAR(30) DEFAULT 'AVAILABLE',
  status VARCHAR(30) DEFAULT 'ACTIVE', created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE food_nutrition (
  food_id VARCHAR(64) PRIMARY KEY REFERENCES food_items(id) ON DELETE CASCADE, calories NUMERIC(10,2), protein_g NUMERIC(10,2),
  carbs_g NUMERIC(10,2), fat_g NUMERIC(10,2), saturated_fat_g NUMERIC(10,2), fiber_g NUMERIC(10,2), sugar_g NUMERIC(10,2),
  added_sugar_g NUMERIC(10,2), sodium_mg NUMERIC(10,2), cholesterol_mg NUMERIC(10,2)
);
CREATE TABLE food_allergens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), food_id VARCHAR(64) NOT NULL REFERENCES food_items(id) ON DELETE CASCADE,
  allergen_code VARCHAR(40) NOT NULL, relationship_type VARCHAR(30) DEFAULT 'CONTAINS', UNIQUE(food_id, allergen_code)
);
CREATE TABLE food_data_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), food_id VARCHAR(64) NOT NULL REFERENCES food_items(id) ON DELETE CASCADE,
  source_type VARCHAR(40) NOT NULL, source_name VARCHAR(250), source_reference TEXT, source_market VARCHAR(50),
  confidence_level VARCHAR(20), verified_at TIMESTAMPTZ
);
CREATE TABLE food_modifiers (
  id VARCHAR(64) PRIMARY KEY, vendor_name VARCHAR(200) NOT NULL, menu_item_name VARCHAR(250), modifier_group VARCHAR(50) NOT NULL,
  name_en VARCHAR(250) NOT NULL, name_ar VARCHAR(250), action VARCHAR(30) NOT NULL, calorie_delta NUMERIC(10,2),
  protein_delta_g NUMERIC(10,2), carbs_delta_g NUMERIC(10,2), fat_delta_g NUMERIC(10,2), sugar_delta_g NUMERIC(10,2),
  sodium_delta_mg NUMERIC(10,2), price_delta NUMERIC(10,2), confidence_level VARCHAR(20)
);
CREATE TABLE food_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, food_id VARCHAR(64),
  food_name VARCHAR(255) NOT NULL, meal_type VARCHAR(20) NOT NULL, entry_method VARCHAR(30) DEFAULT 'MANUAL',
  calories NUMERIC(10,2) DEFAULT 0, protein_g NUMERIC(10,2) DEFAULT 0, carbs_g NUMERIC(10,2) DEFAULT 0,
  fat_g NUMERIC(10,2) DEFAULT 0, sodium_mg NUMERIC(10,2) DEFAULT 0, logged_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_food_items_barcode ON food_items(barcode);
CREATE INDEX idx_food_items_vendor_category ON food_items(vendor_name, category);
CREATE INDEX idx_food_allergens_food ON food_allergens(food_id);
CREATE INDEX idx_food_logs_user_time ON food_logs(user_id, logged_at DESC);
