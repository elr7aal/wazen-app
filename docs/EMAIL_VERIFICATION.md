# WAZEN Email Verification

v64 adds email-ownership verification for new accounts.

## Production configuration

Use the existing SMTP settings:

- `WAZEN_SMTP_HOST`
- `WAZEN_SMTP_PORT`
- `WAZEN_SMTP_USERNAME` when required
- `WAZEN_SMTP_PASSWORD`
- `WAZEN_SMTP_FROM`
- `WAZEN_SMTP_TLS` or `WAZEN_SMTP_SSL`

Add the verification client URL:

```
WAZEN_EMAIL_VERIFY_URL_BASE=https://app.example.com/verify-email
```

The URL must point to the deployed WAZEN client and must be HTTPS for the production launch gate.

The server appends a URL-encoded `token` query parameter. The Flutter client distinguishes verification links from password-reset links by the URL path:

- `/verify-email?token=...` → email verification screen.
- `/reset-password?token=...` → password reset screen.

## Security behavior

- Tokens are random, time-limited and stored only as hashes.
- A token can be used once.
- Issuing a newer verification token invalidates older pending tokens.
- Authenticated resend requests have a cooldown.
- Security audit records verification outcomes without storing the raw token or raw email/IP.
- Permanent account deletion removes pending verification tokens.
- Existing pre-v64 Alpha accounts are grandfathered as verified during migration so upgrades do not lock them out.

## Launch checks

Before production launch:

1. Configure SMTP and `WAZEN_EMAIL_VERIFY_URL_BASE`.
2. Confirm `GET /api/v1/capabilities` reports email verification available.
3. Send a real verification email to a staging mailbox.
4. Open the link on the deployed client and confirm the account becomes verified.
5. Confirm the same link cannot be used twice.
6. Confirm Account shows the verified status.
