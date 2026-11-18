# Render SQLite staging migration rehearsal

This runbook is a template, not authorization to access production. Replace every placeholder, obtain an approved maintenance window, and rehearse with non-production data first.

## Preconditions

- The Render service is live in migration-hold mode with its persistent disk attached.
- Source and target connection secrets come from the approved secret manager and are never written to logs or artifacts.
- The operator has documented approver, start time, abort time, and communication channel.
- The source remains authoritative until cutover is explicitly approved.

## Backup and restore rehearsal

1. Pause staging writers and capture an encrypted, checksummed source snapshot.
2. Record snapshot time, source schema/version, size, checksum, and retention location.
3. Restore into a new isolated database, never over the source or intended target.
4. Verify the restored database opens, has the expected schema/version, and passes row-count and foreign-key checks.
5. Record restore duration and compare it with the recovery-time objective.

## Reconciliation manifest

For every table, record source and target row counts, primary-key minimum/maximum, duplicate primary keys, uniqueness violations, nullability violations, and foreign-key orphan counts. For stable civic and citizen-content IDs, compare ordered ID hashes. Reconcile case-insensitive email collisions before loading users.

No unexplained mismatch may be waived verbally. Record an explicit disposition and approver.

## Restore procedure

1. Download the encrypted GitHub Actions artifact from the recorded backup run.
2. Decrypt only inside the restricted restore job and verify its recorded SHA-256.
3. Run `PRAGMA integrity_check` before upload and again on the Render disk.
4. Install the database atomically as `/app/data/wethepeople.db` while the app remains in migration-hold mode.
5. Set `WTP_MIGRATION_HOLD=0`, keep `WTP_SCHEDULER_ENABLED=0`, and redeploy.
6. Re-run the complete reconciliation manifest against the restored database.

## Cutover rehearsal

1. Put the source in maintenance/read-only mode and confirm writers are stopped.
2. Capture and load the final delta, then repeat reconciliation.
3. Switch only the staging application connection.
4. Run authentication, refresh rotation, password reset, API-key scope, privacy export/anonymization, Housing & Rent, Watch, Discuss, and Solutions smoke tests.
5. Observe errors, latency, locks, and connection saturation for the agreed stabilization period.

## Abort and rollback

Abort on any failed blocking test, unexplained reconciliation mismatch, secret exposure, foreign-key orphan, sequence regression, or material error/latency increase.

Before Render accepts authoritative writes, rollback means keeping DNS on the unchanged Hetzner source and discarding the failed staging target. After Render accepts writes, do not switch to stale SQLite unless a reverse-delta procedure has been separately rehearsed. Pause the service and restore only from a tested backup that contains the accepted writes.

## Evidence to retain

- Approval and operator record
- Redacted commands/configuration identifiers
- Snapshot and restore checksums and timings
- Pre-load and post-load reconciliation manifests
- Sequence-reset report
- Smoke-test results and stabilization metrics
- Cutover or rollback decision with timestamps
