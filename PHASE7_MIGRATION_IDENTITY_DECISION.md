# Phase 7 migration and identity decision

Status: decision gate only. This document does not authorize a production migration, rewrite historical revisions, or connect to production data.

## Decision

Retain the existing FastAPI authentication system and `users.id` as the one canonical identity. Do not introduce an external or second user store during the PostgreSQL move.

Freeze the current Alembic graph as legacy evidence. Build a new canonical baseline from reviewed SQLAlchemy metadata for clean SQLite development and PostgreSQL staging. Existing databases move by an explicit extract, validate, load, validate, and cutover process that preserves every stable primary key and foreign key; they are not replayed through the broken legacy graph.

## Evidence

The legacy graph has three roots:

- `001_initial`, a full-schema snapshot that creates `users`, `api_key_records`, and `audit_logs`.
- `auth001`, a standalone root that creates the same three tables.
- `ratelimit001`, a standalone root.

Revision `6493f7e46ce4` later merges the pipeline, auth, and rate-limit branches, but it cannot prevent duplicate DDL in its ancestors. On a disposable empty SQLite database, `alembic upgrade head` applied `auth001`, `userprefs001`, and `ratelimit001`, then failed in `001_initial` with `table users already exists`. The failure occurs before any Housing & Rent migration.

A new descendant “repair” revision cannot fix a failure in an ancestor. Making the old `create_table` calls conditional would rewrite published migration semantics and still leave a database-specific, internally inconsistent baseline. Neither approach is acceptable for staging or production.

## Canonical identity boundary

Keep:

- `users.id` is the only account identifier. Solution creators/editors/voters, discussion authors/replies/reports/blocks, API keys, watchlists, audit records, and other authenticated records continue to reference it.
- Authentication and authorization derive the user from signed access/refresh credentials; write APIs never accept a caller-supplied user ID.
- Password hashing, generic forgot-password responses, refresh-token rotation/revocation, inactive-user checks, scoped API keys, role checks, and security audit logging remain in the existing service.
- Stable civic-record IDs and citizen-content IDs are copied unchanged to PostgreSQL. PostgreSQL sequences are advanced above the imported maximum after load.

Replace or complete:

- Replace the contradictory role documentation with one enumerated role and permission contract. Current code references `free`, `student`, `pro`, `newsroom`, `enterprise`, and `admin`, while the model comment documents only four roles.
- Add account email verification before treating an account as verified. Residence verification remains a separate, higher assurance attribute.
- Add a first-class account export and deletion/anonymization API with re-authentication, confirmation, audit events, and tests.
- Expand the privacy inventory and erasure workflow to cover verification/location and personalization fields, watchlists, revoked tokens, solutions, votes, discussion posts/replies/reports/blocks/follows/bookmarks/reactions, and snapshot author labels. The current service inventories only a subset and can leave public `author_label` text behind.
- Add a session registry or per-user token epoch so password reset, suspension, and deletion can invalidate all outstanding sessions, not only a presented refresh-token JTI.
- Separate public citizen content, private safety/moderation records, credentials, and security audit data in the database access policy and backup/restore procedure.

Defer:

- External identity providers, a second identity database, HUD integration, AI features, pairwise voting, and broad product expansion.
- Production cutover until staging restore, rollback, privacy, authorization, and reconciliation gates pass.

## Migration architecture

1. Preserve the legacy revision files unchanged in an explicitly labeled legacy location for provenance and existing-install diagnosis.
2. Create a new canonical Alembic environment and baseline revision. It must be generated from reviewed metadata, contain no SQLite-only FTS5 or `PRAGMA` statements on PostgreSQL, and use a distinct version table during rehearsal.
3. Split search by dialect: retain FTS5 for local SQLite; use PostgreSQL full-text search (`tsvector` plus GIN) or a deliberately deferred compatible fallback in staging.
4. Make database compatibility explicit in application jobs. Raw `sqlite3`, `PRAGMA`, `INSERT OR IGNORE`, SQLite JSON functions, snapshot publishing, and SQLite-only backfills must be classified as local/export-only, adapted, or disabled before cutover.
5. Create PostgreSQL staging from the canonical baseline. Never point the first rehearsal at production.
6. Export the source database from a consistent snapshot. Record table counts, primary-key ranges, foreign-key orphan counts, uniqueness checks, nullability checks, and content hashes where practical.
7. Load tables in dependency order inside a controlled migration window. Preserve primary keys exactly, then reset PostgreSQL sequences.
8. Re-run reconciliation and application contract tests against staging. Include authentication, session rotation, privacy export/anonymization, Housing & Rent evidence, Watch, Discuss, and Solutions.
9. Rehearse cutover with writes paused, a final delta load, connection switch, smoke tests, and an observed stabilization period.

## Required staging gates

- A clean canonical-baseline upgrade succeeds on empty SQLite and empty PostgreSQL.
- The ORM schema comparison has no unexplained drift on either dialect.
- Every imported table matches its expected row count; all primary keys remain unchanged; all declared foreign keys have zero orphans.
- Email uniqueness is reconciled case-insensitively before PostgreSQL enforcement.
- Authentication, refresh rotation, password reset, suspension, API-key scopes, and role permissions pass against PostgreSQL.
- User export and anonymization cover every table in the expanded privacy inventory, including public snapshot labels and private moderation records.
- Backup restore creates an independently usable staging database, and the restore is timed and documented.
- Search and all write-heavy social flows pass concurrency tests without SQLite assumptions.
- No secret or private moderation data appears in public snapshots, APIs, logs, or migration artifacts.

## Rollback contract

Before cutover, retain an encrypted, checksummed source snapshot and a tested restore procedure. During cutover, pause writes to avoid divergent authorities. If any blocking smoke test or reconciliation gate fails, restore application reads/writes to the unchanged source database and discard the failed PostgreSQL target; do not attempt reverse row-by-row synchronization.

After PostgreSQL becomes authoritative, keep the source database read-only for a defined observation window. A rollback after new PostgreSQL writes requires a separately rehearsed reverse-delta plan; without that rehearsal, the safe response is service pause and restore from PostgreSQL backup, not an automatic switch to stale SQLite.

## First implementation slice

Create one narrow branch from clean `main` that adds only:

1. A canonical-baseline Alembic environment and schema-drift tests for empty SQLite and PostgreSQL-compatible offline SQL.
2. A migration graph regression test that preserves the legacy collision as documented evidence and prevents the new baseline from importing legacy roots.
3. A machine-readable identity/PII inventory covering all canonical-user foreign keys and public/private/moderation classifications.
4. Staging runbook templates for backup, restore, reconciliation, sequence reset, cutover, and rollback.

Do not copy production data, provision production infrastructure, or change runtime database authority in this first slice.
