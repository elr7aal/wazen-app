# WAZEN Production Launch Checklist

This checklist complements `GET /api/v1/admin/launch-readiness`. The endpoint reports machine-verifiable blockers and warnings; this document covers the manual checks that still require an operator.

## 1. Runtime and secrets

- Set `WAZEN_ENV=production`.
- Use a non-default `JWT_SECRET` of at least 32 characters.
- Use a strong `WAZEN_ADMIN_KEY` of at least 32 characters.
- Configure explicit `WAZEN_CORS_ORIGINS`; never use `*` in production.
- Store all secrets in the deployment provider secret store, not in Git or screenshots.

## 2. Database

- Use persistent PostgreSQL, not SQLite.
- Verify `alembic upgrade head` completes before application startup.
- Verify `/api/v1/readiness` returns `ready: true`.
- Enable managed-provider backups and retention.
- Run and record one restore drill against the actual production/staging PostgreSQL provider.
- Compare Alembic revision and representative row counts after restore.

## 3. Authentication

- Email/password sign-in must work end to end.
- Email verification delivery must be configured.
- `WAZEN_EMAIL_VERIFY_URL_BASE` must be an absolute HTTPS URL.
- Password reset email delivery must be configured.
- `WAZEN_PASSWORD_RESET_URL_BASE` must be an absolute HTTPS URL.
- Run a real verification-email delivery test to a staging mailbox and confirm the link verifies exactly once.
- Run a real reset-email delivery test to a staging mailbox.
- Confirm reset tokens are one-time and old sessions are revoked after reset.
- Confirm login/recovery throttling returns HTTP 429 with `Retry-After` after configured limits.

Apple, Google and mobile OTP are optional for the initial email/password launch and must remain disabled until their secure server-side flows are actually implemented and tested.

## 4. Vision / image analysis

- If image analysis is enabled for users, configure the production Vision provider/API key.
- Confirm image results remain review-only and are never auto-logged.
- If Vision is not configured, keep image-analysis entry points clearly unavailable rather than fabricating a result.

## 5. Observability and security

- Check Admin → Production Launch Gate for zero blockers.
- Check Admin → Operations for readiness, 5xx, slow requests, auth blocks and stale idempotency claims.
- Check Admin → Security Events for login/reset/throttle auditing.
- Confirm no raw email address, IP address, password, access token, refresh token or reset token is stored in security/operational audit payloads.
- Verify request IDs are present on API responses.

## 6. Privacy

- Test user data export.
- Test permanent account deletion with the current password.
- Confirm old access/refresh tokens no longer work after deletion.
- Confirm user-linked security audit rows and hashed email-subject rows are removed according to the privacy flow.

## 7. Mobile and web client

- Flutter tests pass.
- Flutter web release build passes.
- External authentication buttons reflect `/api/v1/capabilities` and unavailable providers stay disabled.
- Validate Arabic RTL and English LTR.
- Validate the Golden Flow, Food Log, Weekly Plan, Progress, Health Limits and Privacy screens on target devices.

## 8. Hosting and domain

- Verify final API and app domains over HTTPS.
- Confirm TLS certificate validity.
- Confirm production CORS only allows intended origins.
- Verify `/api/v1/health` and `/api/v1/readiness` from the public network.
- Confirm the public deployment uses the intended production database and not a local/ephemeral database.

## 9. Native iOS distribution

- Configure signing certificates/profiles.
- Verify secure-storage behavior on a physical iPhone.
- Validate camera, barcode, microphone and any Vision permission flows on-device.
- Complete Ad Hoc/TestFlight/App Store checks when that distribution phase begins.

## Release decision

Do not declare production launch readiness solely from successful unit tests. The automated gate must have zero blockers, CI must be green, and the relevant manual checks above must be completed against the real production/staging services.
