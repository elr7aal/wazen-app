# WAZEN PostgreSQL Backup & Restore Runbook

This runbook is for production/staging operators. Do not store database passwords or full production URLs in Git, logs, tickets, or screenshots.

## Required tools

- PostgreSQL client tools compatible with the server major version: `pg_dump`, `pg_restore`, `psql`, `createdb`.
- A secure shell/environment with temporary access to the database.
- A protected storage destination for backup files.

## Environment

Use a standard PostgreSQL connection URL for PostgreSQL tools:

```bash
export WAZEN_PG_URL='postgresql://USER:PASSWORD@HOST:PORT/DATABASE'
```

The application itself can continue using SQLAlchemy's `postgresql+psycopg://...` URL.

## Create a backup

```bash
umask 077
BACKUP="wazen-$(date -u +%Y%m%dT%H%M%SZ).dump"

pg_dump "$WAZEN_PG_URL" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file="$BACKUP"

test -s "$BACKUP"
sha256sum "$BACKUP" > "$BACKUP.sha256"
```

Store the dump and checksum in the approved encrypted backup location.

## Verify the backup by restoring to a clean database

Never test a restore over the live production database.

Create a clean restore database through the managed PostgreSQL console or standard PostgreSQL tooling, then restore:

```bash
export WAZEN_RESTORE_URL='postgresql://USER:PASSWORD@HOST:PORT/wazen_restore_check'

pg_restore \
  --dbname="$WAZEN_RESTORE_URL" \
  --no-owner \
  --no-privileges \
  --exit-on-error \
  "$BACKUP"
```

## Required verification

```bash
psql "$WAZEN_RESTORE_URL" -tAc "SELECT version_num FROM alembic_version;"
psql "$WAZEN_RESTORE_URL" -tAc "SELECT count(*) FROM food_items;"
psql "$WAZEN_RESTORE_URL" -tAc "SELECT count(*) FROM users;"
```

Then point a temporary WAZEN backend instance at the restored database and verify:

- `GET /api/v1/health` returns HTTP 200.
- `GET /api/v1/readiness` returns `ready: true`.
- Catalog count is non-zero.
- Current Alembic revision matches the source backup.
- Representative authenticated flows work in staging.

## Restore drill frequency

- Run one successful full restore drill before production launch.
- Repeat after material schema/migration changes.
- Repeat on a regular operations cadence after production launch.

The repository CI runs an isolated PostgreSQL backup/restore drill on backend changes. That CI drill validates the procedure and schema mechanics, but it is not a substitute for managed-provider production backup retention and a restore drill against the actual production PostgreSQL service.

## Safety rules

- Do not restore into the live database.
- Do not commit backup dumps.
- Do not print production passwords or URLs to CI logs.
- Keep backup retention and encryption configured at the managed PostgreSQL provider.
- Confirm the restored application is healthy before declaring the backup usable.
