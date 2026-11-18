# WeThePeople Hetzner-to-Render migration preparation

Status: preparation only. Do not apply the Blueprint or change DNS until the
backup, import, reconciliation, and rollback gates below pass.

## Target architecture

- `wethepeople-api-staging`: one paid Render web service built from the
  repository Dockerfile, with a 1 GB persistent disk mounted at `/app/data`.
- The API and scheduler run in the same service instance so both use the same
  SQLite file. The scheduler remains disabled until the restored staging API
  passes its read-only smoke tests.
- PostgreSQL is intentionally deferred. The current application still contains
  SQLite-specific queries and does not install a PostgreSQL driver; creating a
  managed PostgreSQL stack before that work is complete would be unsafe.
- `app.wethepeople.place`: remains on GitHub Pages.
- `api.wethepeople.place`: remains pointed at Hetzner until cutover approval.

The Blueprint intentionally disables startup fetches. External API keys and
email/payment credentials are not stored in Git and must be copied into Render
through its secret environment-variable controls after resource creation.

## Gate 1: Hetzner backups

Before modifying the live server:

1. Create a Hetzner provider snapshot or enable provider backups and record its
   identifier, timestamp, and billed price.
2. Identify the authoritative SQLite file from the running API configuration;
   do not assume a path from repository defaults.
3. Pause the scheduler, then quiesce API writes for the shortest possible
   maintenance window.
4. Create a SQLite online backup, run `PRAGMA integrity_check`, and record its
   SHA-256 checksum and byte size.
5. Store one encrypted copy off the Hetzner server. Never commit the database,
   encryption key, `.env`, or API credentials to Git.
6. Restart the unchanged Hetzner API and scheduler and verify `/health` before
   beginning any Render import.

## Gate 2: Render staging

1. Validate `render.yaml` against the current Render Blueprint schema and CLI.
2. Review the planned paid resources before applying the Blueprint.
3. Create the staging service and its persistent disk in Virginia.
4. Add production-equivalent secret keys through Render without printing or
   committing their values.
5. Keep `WTP_MIGRATION_HOLD=1` and `WTP_SCHEDULER_ENABLED=0` until the verified
   encrypted backup is restored to `/app/data/wethepeople.db`.

## Gate 3: data migration and reconciliation

Use `docs/phase7/STAGING_MIGRATION_RUNBOOK.md` as the blocking checklist.

1. Restore the verified SQLite backup to Render while Hetzner remains the
   authoritative production source.
2. Verify the uploaded SHA-256 and run `PRAGMA integrity_check` before atomically
   installing the database file.
3. Compare every table's row count, ID range, duplicate keys, nullability,
   foreign-key orphans, and ordered stable-ID hashes.
4. Resolve every mismatch; no unexplained mismatch may be waived.
5. Run authentication, representative lookup, votes, bills, promises,
   donations, forecast, Discuss, Watch, Housing, privacy export, and health
   smoke tests.
6. Run the scheduler against staging and verify repeat runs are idempotent.

## Gate 4: cutover

Cutover requires separate approval after the staging report passes.

1. Announce a short maintenance window and stop Hetzner writers.
2. Capture and verify the final SQLite backup/delta.
3. Restore and reconcile the final data on the Render persistent disk.
4. Point `api.wethepeople.place` to the verified Render web service.
5. Verify TLS, CORS, authentication, representative lookup, and scheduler
   health from the public application.
6. Keep Hetzner intact and non-authoritative for at least seven days.

## Rollback boundary

Before Render accepts writes, rollback is DNS back to the unchanged Hetzner
service. After Render accepts writes, pause Render writers and restore only from
a newer verified SQLite backup that includes every accepted write.

