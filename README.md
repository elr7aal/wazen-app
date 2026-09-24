# WAZEN | وازن — Alpha Backend Starter

WAZEN is a personalized food decision platform. This repository now contains the first working backend for the Golden Flow:

`Daily State -> Craving -> Recommendation -> Make It Fit -> Rebalance`

## Backend quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open: `http://127.0.0.1:8000/docs`

## Run tests

```bash
cd backend
pytest -q
```

## Current seed

The recommendation service currently ships with a verified UAE KFC seed subset used for the Golden Flow. It includes nutrition, allergens, and a small set of verified modifier deltas.

## Important product rules

- Severe allergens are hard exclusions before ranking.
- A requested restaurant is preserved as user intent.
- The user can choose an over-target meal; WAZEN rebalances rather than blocking or shaming.
- `Make It Fit` only applies a modifier when the caller confirms that component is part of the meal.
- Missing nutrition data is not interpreted as zero or "healthy".

## v0.3 persistence milestone
The backend now supports persisted users, nutrition profiles and food logs using SQLAlchemy.

### New authenticated endpoints
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET/PATCH /api/v1/users/me`
- `POST /api/v1/food-log`
- `GET /api/v1/food-log/today`
- `DELETE /api/v1/food-log/{log_id}`
- `GET /api/v1/nutrition/today`
- `POST /api/v1/recommendations/for-me`

`DATABASE_URL` defaults to SQLite for local/test convenience. Set the provided PostgreSQL URL in `.env` for deployment.

## v0.4 — Unified Database Catalog

The alpha backend now seeds the food catalog into the configured SQL database from `backend/app/data/catalog_seed_v5.json` on first boot.

Current seed coverage:
- 70 restaurant food records (McDonald's UAE + KFC UAE)
- 15 UAE grocery records
- 5 verified KFC modifiers imported (sample modifiers are intentionally skipped)

New database-backed endpoints:
- `GET /api/v1/foods/search`
- `GET /api/v1/foods/{food_id}`
- `GET /api/v1/foods/barcode/{barcode}`
- `POST /api/v1/recommendations/now` now queries SQL instead of `kfc_uae.json`
- `POST /api/v1/recommendations/for-me` uses persisted user/day data plus the SQL catalog
- `POST /api/v1/recommendations/make-it-fit` loads food + modifiers from SQL

Data provenance is stored in `food_data_sources`, and hard-allergy filtering only treats explicit `CONTAINS` relationships as hard exclusions. Cross-contact warnings remain warnings instead of silently excluding foods.

### Run tests

```bash
cd backend
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///./test.db pytest -q
```

Expected current result: **14 passed**.


## v5 Golden Flow endpoints
- `POST /api/v1/food-log/from-catalog`
- `POST /api/v1/golden-flow`

The catalog item can now be logged by `food_id`; nutrition is copied from the verified catalog and the user's daily state is recalculated automatically.

## v6 — Mobile Alpha
A Flutter Arabic-first mobile client has been added under `mobile/` and wired to the live FastAPI Golden Flow:
Auth → Home → craving input → recommendations → food detail → Add to Today → refreshed daily state.

## v7 Make It Fit
- Interactive mobile Make It Fit screen.
- Verified component-level choices only.
- GET `/api/v1/foods/{food_id}/make-it-fit-options`
- POST `/api/v1/food-log/from-modified-catalog`
- Modified nutrition snapshot is saved to the Food Log.

## v8 Rebalance
- Personalized post-meal Rebalance screen.
- GET `/api/v1/rebalance/for-me`
- Recalculates remaining calories/macros/protein from persisted Food Log.
- Returns up to 5 next food options from the unified catalog.
- Mobile routes to Rebalance after normal or modified meal logging.

## v9 Food Log
- Full Today/Food Log screen grouped into breakfast, lunch, dinner and snacks.
- Edit meal type/calories/protein from the app.
- Delete entries and immediately recalculate Daily State.
- Bottom navigation connects Home, Today and Discover.
- PATCH `/api/v1/food-log/{log_id}` added with user ownership protection.

## v10 Add Food
Unified Add Food flow:
- Catalog search
- Natural-language text matching with mandatory review
- Camera photo intake with an explicit Vision-provider adapter contract; this build never fabricates image analysis when no provider is configured
- Camera barcode scan and catalog lookup
- Common review screen with quantity and meal selection before logging
- All confirmed inputs converge on the same persisted Food Log

- Arabic-English food aliases are supported for common MVP terms such as زينجر → Zinger and برغر → Burger.

## v11 Vision + Voice
- Real image analysis uses the OpenAI Responses API when `OPENAI_API_KEY` is configured.
- Image inputs are sent as Base64 data URLs and remain `AI Estimate` until user review.
- Voice input uses `speech_to_text` on device with Arabic UAE locale, then feeds recognized text through the same text-parser review flow.
- No image or voice result is automatically logged.

## v12 Onboarding
- Four-step Arabic-first onboarding: body basics, goal/activity/budget, severe allergies, preferences/dislikes.
- Generic starting targets are calculated with Mifflin-St Jeor + activity factor and goal adjustment.
- Protein/fat/carbohydrate targets are derived and persisted.
- Severe allergies are stored as hard exclusions; preferences/dislikes are separate ranking signals.
- New and returning incomplete accounts are routed to onboarding before Home.
- Calculated targets are a general-wellness starting estimate and remain editable.

## v13 Preference Learning
- Preference score uses onboarding likes/dislikes with food-term aliases (e.g. CHICKEN also matches Zinger/Twister/Nuggets).
- Repeated logged foods create a small passive positive affinity.
- Explicit SAVE/ACCEPT/ORDER feedback increases affinity; REJECT decreases it.
- Preference learning is capped and never overrides severe-allergy hard exclusions or health rules.
- Mobile recommendation cards include Save and Not-for-me controls.

## v14 Profile & Plan
- Full Arabic Account & Plan screen.
- Edit weight, target weight, goal, activity, budget, allergies, likes/dislikes and daily macro targets.
- Recalculate generic targets from current body/profile data on demand.
- "Why WAZEN recommends this" insight panel explains safety exclusions, stated preferences, repeated choices and rejection signals.
- Bottom navigation now includes Account.

## v15 iOS Cloud Build + PWA
- GitHub Pages PWA workflow for iPhone Home Screen installation without App Store.
- macOS GitHub Actions validation build for iOS without signing.
- Ad Hoc IPA workflow prepared for Apple Developer signing and registered devices.
- Backend Dockerfile + Railway configuration added.
- `API_BASE_URL` is configurable at build time.
- CORS support added for hosted PWA.
- See `docs/IOS_NO_MAC_SETUP_AR.md`.


## v16 — Admin & Data Operations
- Admin food review queue with APPROVE / REJECT / FLAG.
- Admin audit history for review and import actions.
- JSON and CSV food import with dry-run mode.
- Validation for required IDs/names, invalid or negative numeric values, duplicate IDs/barcodes and existing barcode conflicts.
- Lightweight `admin/index.html` review/import console.
- Admin endpoints protected by `WAZEN_ADMIN_KEY`.
- Backend CI established; v16 baseline: 49 passing tests.

## v17 — Weekly Plan + Progress
- Persisted 7-day meal plan with breakfast, lunch, dinner and snack.
- Meal allocation uses the user's calorie target and excludes explicit severe allergens before planning.
- Per-day rebalance and full-week regeneration.
- Progress summaries for 7 / 30 / 90 days.
- Goal-day tracking, average calories/protein, restaurant spend from logged catalog items and persisted weight history.
- New Arabic-first mobile “خطتي” tab with weekly plan and progress views.
- Bottom navigation expanded to: الرئيسية / يومي / اكتشف / خطتي / حسابي.
- Backend v17 baseline: **52 passing tests**.

## v18 — First-run Experience
- First-launch splash, language selection, welcome screen and account-method screen.
- Arabic / English preference is persisted and updates app locale + text direction.
- Email sign-in/register UI cleaned for real use; Alpha demo credentials removed.
- API URL moved behind advanced connection settings.
- Apple, Google and mobile-number sign-in appear only as clearly unavailable placeholders until a secure provider is connected; they do not simulate authentication.
