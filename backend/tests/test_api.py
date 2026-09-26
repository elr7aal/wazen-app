from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DAILY = {
    "target_calories": 2000,
    "consumed_calories": 1300,
    "activity_credit": 0,
    "target_protein_g": 140,
    "consumed_protein_g": 102,
    "target_carbs_g": 210,
    "consumed_carbs_g": 148,
    "target_fat_g": 65,
    "consumed_fat_g": 42,
    "sodium_max_mg": 2300,
    "consumed_sodium_mg": 1320
}


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_daily_state():
    r = client.post("/api/v1/daily-state/calculate", json=DAILY)
    d = r.json()["data"]
    assert d["remaining_calories"] == 700
    assert d["protein_gap_g"] == 38
    assert d["sodium_remaining_mg"] == 980


def test_craving_parse_kfc():
    r = client.post("/api/v1/cravings/parse", json={"text":"أبي برغر من KFC تحت 600 سعرة"})
    d = r.json()["data"]
    assert d["restaurant"] == "KFC UAE"
    assert d["food_category"] == "BURGERS"
    assert d["max_calories"] == 600


def test_recommendations_respect_vendor_and_calorie_context():
    payload = {
        "daily_state": DAILY,
        "vendor": "KFC UAE",
        "category": "BURGERS",
        "max_calories": 600,
        "severe_allergens": [],
        "allow_modifications": True
    }
    r = client.post("/api/v1/recommendations/now", json=payload)
    assert r.status_code == 200
    results = r.json()["data"]["results"]
    assert results
    assert all(x["vendor"] == "KFC UAE" for x in results)
    eligible = [x for x in results if x["decision"] == "ELIGIBLE"]
    assert eligible
    assert all(x["nutrition"]["calories"] <= 600 for x in eligible)


def test_severe_allergen_exclusion():
    payload = {
        "daily_state": DAILY,
        "vendor": "KFC UAE",
        "category": "BURGERS",
        "severe_allergens": ["SESAME"],
        "allow_modifications": True
    }
    r = client.post("/api/v1/recommendations/now", json=payload)
    data = r.json()["data"]
    excluded_ids = {x["food_id"] for x in data["excluded"]}
    assert "KFC-AE-014" in excluded_ids
    assert "KFC-AE-015" in excluded_ids


def test_make_it_fit_only_applies_explicit_components():
    payload = {
        "food_id": "KFC-AE-015",
        "daily_state": DAILY,
        "included_components": ["REGULAR_PEPSI_453ML", "LARGE_FRIES"]
    }
    r = client.post("/api/v1/recommendations/make-it-fit", json=payload)
    d = r.json()["data"]
    assert round(d["calories_saved"], 1) == 363.3
    assert round(d["modified_nutrition"]["calories"], 1) == 556.7
    assert d["fits_remaining_calories"] is True


def test_rebalance_preserves_user_choice():
    payload = {
        "daily_state": DAILY,
        "added_calories": 920,
        "added_protein_g": 56.2,
        "added_carbs_g": 64.4,
        "added_fat_g": 50.1,
        "added_sodium_mg": 766.1
    }
    r = client.post("/api/v1/day/rebalance", json=payload)
    d = r.json()["data"]
    assert d["user_choice_preserved"] is True
    assert d["updated_state"]["remaining_calories"] == 0
    assert "above the current plan" in d["message"]


def test_unified_catalog_contains_kfc_and_mcdonalds():
    kfc = client.get('/api/v1/foods/search', params={'vendor':'KFC UAE','category':'BURGERS','limit':50})
    assert kfc.status_code == 200, kfc.text
    k_items = kfc.json()['data']['items']
    assert len(k_items) >= 7
    assert any(x['name'] == 'Zinger Sandwich' for x in k_items)

    mcd = client.get('/api/v1/foods/search', params={'vendor':"McDonald's UAE",'q':'Big Mac'})
    assert mcd.status_code == 200, mcd.text
    m_items = mcd.json()['data']['items']
    assert any(x['name'] == 'Big Mac' and x['nutrition']['calories'] == 549 for x in m_items)


def test_catalog_nutrition_filters():
    r = client.get('/api/v1/foods/search', params={'vendor':'KFC UAE','category':'BURGERS','max_calories':600,'min_protein_g':25})
    assert r.status_code == 200
    items = r.json()['data']['items']
    assert items
    assert all(x['nutrition']['calories'] <= 600 for x in items)
    assert all(x['nutrition']['protein_g'] >= 25 for x in items)
