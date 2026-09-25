# WAZEN Password Reset Email Delivery

WAZEN supports SMTP delivery for password-reset links. No SMTP credentials should be committed to the repository.

## Required environment variables

- `WAZEN_SMTP_HOST`
- `WAZEN_SMTP_PORT` (default `587`)
- `WAZEN_SMTP_FROM`
- `WAZEN_PASSWORD_RESET_URL_BASE`

Optional authentication and transport variables:

- `WAZEN_SMTP_USERNAME`
- `WAZEN_SMTP_PASSWORD`
- `WAZEN_SMTP_TLS=true|false` (default `true`)
- `WAZEN_SMTP_SSL=true|false` (default `false`)
- `WAZEN_SMTP_TIMEOUT_SECONDS` (default `10`)

Example reset URL base:

```text
https://app.example.com/reset-password
```

The reset token is appended as a URL-encoded `token` query parameter.

## Enumeration safety

`POST /api/v1/auth/forgot-password` deliberately returns the same public acceptance response for existing and non-existing accounts.

`delivery_available` only describes whether email delivery is globally configured in the current environment. It does not reveal whether the submitted email exists.

Provider delivery status is written only to the restricted security audit, not returned to the public caller.

## Debug tokens

`WAZEN_PASSWORD_RESET_DEBUG=1` can expose a reset token only outside production. Do not enable it in production.

## Operational checks

Before production launch:

1. Configure the SMTP credentials through the deployment secret store.
2. Verify a real delivery to a staging mailbox.
3. Verify the reset link opens the intended application/web reset route.
4. Confirm one-time token consumption.
5. Confirm old refresh sessions are invalid after a successful password reset.
6. Confirm Security Events records `PASSWORD_RESET_REQUEST` and `PASSWORD_RESET` without raw email/IP/token values.
