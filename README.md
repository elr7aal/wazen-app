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


## v19 — Secure Sessions
- Access + refresh token sessions.
- Refresh token rotation; reused refresh tokens are rejected.
- Logout revokes the active refresh session; all-session revocation is supported.
- Password reset tokens are single-use, expiring and revoke old sessions after a successful reset.
- Password-reset responses do not reveal whether an email exists.
- Mobile stores refresh tokens and restores an expired session automatically.
- Password recovery UI clearly reports when email delivery is not yet configured.
- Backend v19 baseline: **56 passing tests**.

## v20 — Goal History
- Goal/profile snapshots are retained on onboarding, meaningful profile updates and plan recalculation.
- Duplicate snapshots are skipped.
- New `GET /api/v1/profile/history` endpoint.
- Account screen shows recent plan/goal history including weight, target weight and calorie target.

## v21 — Preference Levels
- Explicit preferences support: `LOVE / LIKE / NEUTRAL / DISLIKE / NEVER_SHOW`.
- Preferences can target a food term/category or a specific food item.
- `NEVER_SHOW` is applied before ranking as an explicit user exclusion.
- LOVE/LIKE/DISLIKE adjust preference scoring but never override severe-allergy exclusions.
- Account UI supports five-level preference controls and synchronizes legacy like/dislike signals.
- Backend v21 baseline: **62 passing tests**.

## v22 — Health & Safety Limits
- Explicit user/clinician nutrition limits with MAX/MIN and SOFT/HARD behavior.
- HARD limits are applied before ranking and also respected by weekly plans.
- Missing nutrition required by a HARD limit is treated as unknown/unsafe for that rule, never as zero.
- Mobile Health Limits management screen linked from Account/Safety.
- Backend v22 baseline: **66 passing tests**.

## v23 — Food Catalog Search
- Arabic/English synonym search, including برغر / برجر / burger families.
- Filters for vendor, brand, category, food type, calories, protein, sodium, fiber and price.
- Mobile search supports All / Restaurants / Grocery plus nutrition and price filters.

## v24 — Food Log Favorites
- Duplicate any logged meal.
- Save a log as a reusable favorite.
- Re-log favorites with one tap.
- Daily totals recalculate immediately after these operations.

## v25 — Structured Natural-language Logging
- Arabic/English multi-item text parsing.
- Conservative portion and unit estimates.
- Per-item candidate lists and confidence.
- preview_required=true and auto_saved=false by contract; text parsing never saves without user confirmation.

## v26 — Image Review Contract
- Image analysis remains review-only.
- AI-estimated food/portion data is never auto-saved.
- Low/unknown confidence remains visible to the user.

## v27 — Daily Nutrition + Activity
- Fiber target/consumption/remaining added to the daily engine.
- Manual Activity Credit support with persisted activity logs.
- Fiber is preserved across modified meals, favorites and goal history.

## v28 — Structured Craving Parser
- Arabic/English parsing for restaurant, category, calorie, protein and budget constraints.
- Currency context is required before numbers are interpreted as budget.
- Parsed constraints are shown to the user before recommendation results.

## v29 — Candidate Filtering Audit
- Severe allergy, explicit NEVER_SHOW, hard health limits, unavailable foods and insufficient nutrition are filtered before ranking.
- Exclusion reasons are persisted with request context.
- Added GET /api/v1/recommendations/exclusions.
- Fixed recommendation argument mapping so budget cannot be misread as a protein constraint.

## v30 — Ranking Engine v1 Audit
- Ranked recommendation decisions are persisted with rank, component scores, reasons, warnings and request context.
- Added GET /api/v1/recommendations/decisions.
- Ranking tests enforce 0–100 score bounds, stable decision priority and preservation of an explicitly requested vendor.

## v31 — Make It Fit Hardening
- Duplicate modifier components are de-duplicated before nutrition math.
- Core requested food is explicitly preserved.
- Before/after nutrition and nutrition delta are returned.
- Only verified, explicitly selected components are applied.

## v32 — Rebalance Day Hardening
- User choice is explicitly preserved after logging, including when the day goes over the current calorie target.
- Post-overage recommendations use a lighter follow-up ceiling rather than blocking the chosen meal.
- Neutral Arabic copy avoids guilt/shaming language.

## v33 — Recommendation Card Completeness
- Recommendation cards show price when known.
- Health/safety/budget warnings are visible instead of hidden.
- Source confidence remains visible on every card.

## v34 — Food Detail Provenance
- Food detail now includes source name, confidence, reference and last verification date.
- Missing nutrition values remain visibly unavailable (—) and are never presented as low/zero.

## v35 — Admin Data Review Completion
- Admin can edit catalog/nutrition/allergen data with full before/after audit snapshots.
- Duplicate foods can be merged into a canonical record while preserving the source as MERGED.
- Food-log, favorites, weekly-plan and recommendation references are remapped during merge.
- Admin UI now exposes Edit and Merge actions in addition to review/import.

## v36 — Official Alpha QA Gate
- Added automated QA-001 through QA-010 from the engineering acceptance checklist.
- Daily math, edit/delete, allergy filtering, craving parsing, Make It Fit, user override, missing sodium and source provenance are all enforced in CI.

## v37 — Explicit Condition Context
- Optional condition context is stored separately from nutrition limits.
- Condition context alone never changes recommendations or creates medical limits.
- Any effective nutrition restriction still requires an explicit Health Limit.

## v38 — Session Security
- Active authentication sessions can be listed.
- Account UI shows active-session count.
- “Logout all devices” revokes every active refresh session.

## v39 — Database Migration Safety
- Added Alembic migration framework.
- Idempotent current-schema baseline supports fresh and older Alpha databases.
- Known additive Alpha columns are reconciled safely.
- Migration baseline is covered by automated tests.

## v40 — Auth Acceptance Hardening
- Registration and password reset enforce 8+ characters with uppercase, lowercase and numeric characters.
- Expired access tokens are explicitly tested and rejected.

## v41 — Production Configuration Guardrails
- Production startup rejects default/short JWT secrets, wildcard CORS and SQLite.
- Runtime health output exposes only safe environment/database-mode metadata.

## v42 — Secure Mobile Token Storage
- Access and refresh tokens moved out of SharedPreferences into secure storage.
- Existing pre-v42 tokens are migrated once and deleted from legacy preferences.

## v43 — Automatic Session Refresh
- Authenticated mobile requests retry once after a single-flight refresh.
- Concurrent 401s do not rotate the same refresh token multiple times.
- Transient network failure during refresh does not erase the local session.

## v44 — Recommendation Contract Alignment
- Direct /recommendations/for-me requests now support min_protein_g consistently with Golden Flow.
- Decision audit retains the protein constraint in request context.

## v45 — Password UX Alignment
- Registration screen explains the backend password policy and validates it before submission.

## v46 — Migration-first Container Startup
- Backend Docker startup runs alembic upgrade head before Uvicorn.
- CI builds the Docker image and smoke-tests the migrated container.

## v47 — Operational Readiness
- Added /api/v1/readiness for database/catalog/migration checks.
- Every HTTP response gets an X-Request-ID for request tracing.
- Docker smoke test now validates readiness rather than liveness only.
- Current backend baseline: **122 passing tests**.
- Latest Flutter web validation: **passing**.


## v48 — Idempotent Mobile Writes
- Added persisted Idempotency-Key support for retry-sensitive food-log writes.
- Same key + same payload replays the original response without creating a duplicate log.
- Same key + different payload returns HTTP 409.
- Covered manual food logging, catalog logging, modified-catalog logging, duplicate meal logging and favorite re-logging.
- Flutter generates one idempotency key per user action and preserves it across automatic auth-refresh retries.
- Added Alembic revision `0002_idempotency` and migration-head coverage.


## v49 — Retry Resilience Completion
- Golden Flow accepts Idempotency-Key so an auth/network retry cannot duplicate an optional auto-logged meal or duplicate the same audited decision response.
- Manual activity credit logging is idempotent and cannot double-count calories after a retry.
- Flutter preserves the same per-action key through automatic token refresh/retry for both flows.
- Backend v49 baseline: **130 passing tests**.
