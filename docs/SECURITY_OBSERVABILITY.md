# Security audit and operational monitoring

## Handoff reconciliation — 2026-09-26

The v56 handoff describes an earlier checkpoint. At baseline commit
`dec62cb6d7322db7724097861d20ad1ad28fc590`, v56 and v57 were already implemented,
with later work through v65 present. This follow-up preserves that work and
completes missing v56 acceptance coverage rather than replaying old milestones.

- v56 audit tests now cover login success/failure/throttling, refresh rotation
  success and replay failure, single-session/all-session logout, reset requests,
  reset success/failure/throttling, admin authorization and filters, hashed
  email/network storage, bounded request IDs, retention and account deletion.
- Deletion tests verify subject-only events are removed and other users' events
  are preserved.
- Security and operational event rows escape all displayed values, including
  caller-supplied request IDs, paths, details and security API error messages.
- Four Node regression tests cover unsafe markup, filter serialization and empty
  results. Backend CI runs these tests and also triggers for admin changes.

Validation before commit: **201 backend tests passed; 4 admin UI tests passed**.
Remote CI must additionally pass Docker migration/readiness and the existing
PostgreSQL backup/restore drill. No deployment was requested or performed.

## Endpoints

All endpoints below require the existing `X-WAZEN-ADMIN-KEY` credential.
Never put this key in a URL, a public client or a screenshot.

| Endpoint | Purpose | Filters |
| --- | --- | --- |
| `GET /api/v1/admin/security-events` | Authentication/security ledger | `event_type`, `outcome`, `limit` |
| `GET /api/v1/admin/operational-events` | HTTP 5xx and slow-request ledger | `event_type`, `status_code`, `limit` |
| `GET /api/v1/admin/operations/summary` | Readiness, recent errors, security blocks and idempotency health | None |

Use the Security Events and Operations sections in `admin/index.html` to inspect
these endpoints. Raw email and client-host fields are hashed before persistence.
Security audit rows are excluded from account exports. Account deletion clears
user-linked rows and rows matching the account's hashed email subject.
Request IDs are caller-supplied correlation labels, bounded to 80 characters;
clients must not place personal data or credentials in them. Operational paths
are currently stored as bounded URL paths, so clients must not put secrets in
path segments. Query strings, bodies and authorization headers are not logged.

## Retention and thresholds

| Setting | Default | Minimum | Behavior |
| --- | --- | --- | --- |
| `WAZEN_SECURITY_EVENT_RETENTION_DAYS` | 90 days | 7 days | Security ledger retention |
| `WAZEN_OPERATIONAL_RETENTION_DAYS` | 30 days | 7 days | Operational ledger retention |
| `WAZEN_SLOW_REQUEST_MS` | 1500 ms | 250 ms | Slow request threshold |
| `WAZEN_IDEMPOTENCY_STALE_SECONDS` | 120 seconds | 30 seconds | Stale pending-claim threshold |

Retention cleanup runs when new events are written; it is not a scheduled purge.
Security subject/client digests use the existing throttle HMAC secret selection:
`WAZEN_THROTTLE_SECRET`, then `JWT_SECRET`, then `WAZEN_SECRET`, with a development
fallback. Maintain a stable strong secret in production; changing it also changes
subject matching for historical hashed rows.

The operational summary returns alert-ready data. It does not send external
notifications or configure a monitoring provider. `/api/v1/health` is liveness;
`/api/v1/readiness` checks database/catalog/migration readiness. Inspect the
summary's alert codes before taking action; do not restart deployment as part
of an audit review.

## Reproduce validation

```sh
cd backend
PYTHONPATH=. WAZEN_SECRET=test-secret WAZEN_ADMIN_KEY=test-admin-key pytest -q
cd ..
node --test admin/audit-ui.test.cjs
```

GitHub Actions runs the full backend suite, the admin tests, Docker smoke checks
and the PostgreSQL restore drill. Flutter was unchanged by this follow-up; its
existing workflow validates tests and a release web build without deployment.
