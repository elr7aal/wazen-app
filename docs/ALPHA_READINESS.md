# WAZEN Alpha Readiness

Updated: 2026-09-25

## Automated quality gate

- Backend: **164 / 164 tests passing**
- Flutter model tests: passing
- Flutter web validation build: passing
- Migration-first Docker readiness smoke test: passing
- Deployment: intentionally paused; this document covers application readiness, not hosting readiness.

## Official QA checklist

| QA | Scenario | Status | Automated evidence |
|---|---|---|---|
| QA-001 | Daily math: 400 + 600 + 300 = 1300, remaining 700 | PASS | test_alpha_acceptance_v36.py |
| QA-002 | Edit meal 600 → 750 reduces remaining by 150 | PASS | test_alpha_acceptance_v36.py |
| QA-003 | Delete 300 kcal snack increases remaining by 300 | PASS | test_alpha_acceptance_v36.py |
| QA-004 | Severe MILK allergy never reaches ranking | PASS | test_alpha_acceptance_v36.py + exclusion audit |
| QA-005 | Arabic Hardee's burger craving preserves restaurant | PASS | test_alpha_acceptance_v36.py |
| QA-006 | Pizza under 500 kcal constraint parses correctly | PASS | test_alpha_acceptance_v36.py |
| QA-007 | Make It Fit verified modifiers recalculate nutrition | PASS | test_alpha_acceptance_v36.py + test_make_it_fit_mobile_backend.py |
| QA-008 | High-calorie user choice is accepted and day rebalanced | PASS | test_alpha_acceptance_v36.py + test_rebalance_for_me.py |
| QA-009 | Missing sodium under a HARD sodium rule is not treated as safe/low | PASS | test_alpha_acceptance_v36.py |
| QA-010 | Source confidence and last verification metadata are exposed | PASS | test_alpha_acceptance_v36.py + Flutter food detail |

## Engineering backlog gate

| Area | Current state |
|---|---|
| WAZ-001 Foundation | PASS |
| WAZ-002 Authentication | PASS for email/password + refresh/logout/reset contracts |
| WAZ-003 Profile & Goals | PASS; goal history retained |
| WAZ-004 Preferences | PASS; LOVE/LIKE/NEUTRAL/DISLIKE/NEVER_SHOW |
| WAZ-005 Health & Allergies | PASS for severe allergies + explicit health/clinician limits |
| WAZ-006 Food Catalog | PASS; bilingual synonym search + filters + detail + barcode |
| WAZ-007 Food Logging | PASS; add/edit/delete/duplicate/favorite |
| WAZ-008 Natural Language Logging | PASS; multi-item review-only flow |
| WAZ-009 Image Logging | PASS contract; actual AI analysis depends on configured vision provider |
| WAZ-010 Daily Nutrition | PASS; calories/macros/fiber/sodium/activity credit |
| WAZ-011 Craving Parser | PASS; bilingual structured constraints |
| WAZ-012 Candidate Filtering | PASS; exclusions happen before ranking and are audited |
| WAZ-013 Ranking Engine v1 | PASS; bounded scores + stored reasons/decisions |
| WAZ-014 Make It Fit | PASS; verified modifiers + before/after nutrition |
| WAZ-015 Rebalance Day | PASS; user choice preserved, neutral follow-up |
| WAZ-016 Home | PASS |
| WAZ-017 Recommendation Results | PASS |
| WAZ-018 Food Detail | PASS; provenance and uncertainty visible |
| WAZ-019 Admin Data Review | PASS; search/edit/review/flag/merge/audit |
| WAZ-020 Seed Importer | PASS; CSV/JSON, dry run, validation, duplicate checks |

## External integrations intentionally not represented as complete

These do not block local Alpha application logic, but they are not considered production-ready until connected and tested:

- Apple Sign in provider.
- Google Sign in provider.
- Mobile-number OTP provider.
- Password-reset email delivery provider.
- Production Vision provider/API key for image analysis.
- Production PostgreSQL credentials and managed-provider backup retention remain external; repository CI now performs a full PostgreSQL dump/restore/readiness drill.
- Native iOS signing / App Store or Ad Hoc distribution.
- Production hosting/domain/deployment verification.

## Safety invariants

1. Severe explicit allergens are filtered before ranking.
2. HARD health limits are filtered before ranking.
3. Missing nutrient data required by a HARD rule is treated as unknown, not zero.
4. NEVER_SHOW is an explicit user exclusion.
5. Preference signals never override hard safety rules.
6. AI/text/image inputs require review before save.
7. Make It Fit only applies verified components explicitly confirmed by the user.
8. Rebalance preserves the user's chosen meal and adjusts later suggestions without guilt/shaming copy.
9. Recommendation exclusions and ranked decisions are auditable.
10. Source confidence and verification metadata stay visible where available.


## Post-gate hardening completed

- v37: explicit condition context, non-prescriptive by design.
- v38: active sessions and logout-all-devices.
- v39: Alembic baseline and migration idempotency.
- v40: password policy and expired-access-token acceptance tests.
- v41: production runtime guardrails for JWT/CORS/database.
- v42: secure mobile token storage with legacy migration.
- v43: automatic single-flight access-token refresh and one retry.
- v44: direct recommendation contract aligned with protein constraints.
- v45: registration UI aligned with password policy.
- v46: Docker starts only after successful database migration.
- v47: readiness endpoint, request IDs and migrated-container smoke testing.
- v48–v51: idempotent mutation safety, retry resilience and stale-claim recovery.
- v52: privacy export and permanent account deletion.
- v53–v54: data freshness and source-aware ranking.
- v55: database-backed authentication abuse protection.
- v56: privacy-preserving security event audit.
- v57: production observability for 5xx/slow requests plus operations alert summary.
- v58: automated PostgreSQL backup/restore/readiness drill plus operator runbook.
- v59: enumeration-safe SMTP password-reset delivery adapter.
- v60: truthful integration capability registry and capability-aware client options.
- v61: machine-readable Production Launch Gate plus operator launch checklist.
- v62: capability-aware image logging UI.
- v63: password-reset completion screen and client link routing.
- v64: email ownership verification with one-time links, resend cooldown and production gate integration.

Current verified engineering baseline: **179 backend tests passing**, Flutter validation passing, Docker migration/readiness smoke passing, PostgreSQL backup/restore drill passing.
