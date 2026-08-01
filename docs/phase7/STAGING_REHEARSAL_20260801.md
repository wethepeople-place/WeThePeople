# Phase 7 local PostgreSQL rehearsal evidence — 2026-08-01

## Scope and authority

- Authorized target: disposable local PostgreSQL only.
- PostgreSQL: 17.10 on `127.0.0.1:55432`.
- Databases: `wtp_rehearsal` and isolated `wtp_rehearsal_restore`.
- Application owner: `wtp_rehearsal`, confirmed `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, and `NOREPLICATION`.
- Data: synthetic records only. No production data was accessed or copied.
- Runtime `WTP_DB_URL` and database authority were not changed.

## Canonical migration

- Canonical head: `canonical_admin_suspend_001`.
- Public tables after upgrade: 144.
- Live PostgreSQL upgrade: passed after repairing the Boolean-addition check constraint found by this rehearsal.
- Live Alembic drift check: `No new upgrade operations detected` after adding dialect-safe JSON default comparison.

## Synthetic stable-ID chain

| Table | Rows | Minimum ID | Maximum ID | Ordered-ID MD5 |
|---|---:|---:|---:|---|
| `users` | 1 | 700001 | 700001 | `c543e78865002ff0471267d0cf4dfac2` |
| `discussion_posts` | 1 | 710001 | 710001 | `e5c495ee8b76bea090b1f98147514a8b` |
| `proposals` | 1 | 720001 | 720001 | `a64f92d0247550bdd5e4f0cb21713135` |
| `solution_revisions` | 1 | 730001 | 730001 | `21a18c17473c64160d6f54fb5cfd1f5b` |

- Orphan checks for discussion authors, proposal authors, solution parents, and revision editors: 0.
- Sequences were reset to imported maxima.
- Restored `users` sequence generated ID 700002, proving it advanced beyond stable imported ID 700001.

## Backup and restore

- Archive format: PostgreSQL custom (`pg_dump -Fc`).
- Archive size: 731,767 bytes.
- Backup duration: 0.246 seconds.
- SHA-256: `F6FFF23C16F9448007E6EC41994F90A2EE0736E372FC9A36630F3475E3388A0B`.
- Restore target was separate from the source database.
- Restore duration: 1.32 seconds.
- Source/restored row counts, ID ranges, and ordered-ID hashes: exact match.
- Restored orphan total: 0.

## Findings repaired

1. `ck_discussion_attachment_one_target` added Boolean expressions, which SQLite accepted but PostgreSQL rejected. The canonical schema and ORM now use portable `CASE ... THEN 1 ELSE 0 END` terms.
2. Alembic's PostgreSQL default comparator attempted `json = unknown`, but PostgreSQL `json` has no equality operator. Canonical migrations now compare normalized JSON defaults in Python while retaining all other drift checks.

## Abort and rollback result

- The first PostgreSQL migration failed transactionally on the check constraint and left zero public tables, demonstrating the pre-write abort boundary.
- The source database remained unchanged throughout restore testing.
- No staging cutover was attempted; the application remains on its existing runtime database authority.
