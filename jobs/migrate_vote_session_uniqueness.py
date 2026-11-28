"""Make roll-call uniqueness session-aware for SQLite production databases.

House and Senate roll numbers restart for each congressional session.  The
legacy constraint omitted ``vote_session``, causing valid 2026 records to
collide with 2025 records from the same Congress.

This migration is intentionally standalone because the production SQLite
database predates the current Alembic history.  It creates an online backup,
rebuilds only the ``votes`` table in one transaction, restores explicit
indexes, and verifies foreign keys before returning.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


OLD_CONSTRAINT = "uq_votes_congress_chamber_roll"
NEW_CONSTRAINT = "uq_votes_congress_chamber_session_roll"
TEMP_TABLE = "votes__session_migration"


def _normalise_sql(sql: str) -> str:
    return re.sub(r'["`\[\]\s]+', "", sql.lower())


def _has_session_constraint(create_sql: str) -> bool:
    return "unique(congress,chamber,vote_session,roll_number)" in _normalise_sql(create_sql)


def _replace_constraint(create_sql: str) -> str:
    named = re.compile(
        rf"CONSTRAINT\s+[\"`\[]?{OLD_CONSTRAINT}[\"`\]]?\s+"
        r"UNIQUE\s*\(\s*congress\s*,\s*chamber\s*,\s*roll_number\s*\)",
        re.IGNORECASE,
    )
    replacement = (
        f"CONSTRAINT {NEW_CONSTRAINT} "
        "UNIQUE (congress, chamber, vote_session, roll_number)"
    )
    updated, count = named.subn(replacement, create_sql, count=1)
    if count == 0:
        unnamed = re.compile(
            r"UNIQUE\s*\(\s*congress\s*,\s*chamber\s*,\s*roll_number\s*\)",
            re.IGNORECASE,
        )
        updated, count = unnamed.subn(replacement, create_sql, count=1)
    if count != 1:
        raise RuntimeError("legacy vote uniqueness constraint was not found exactly once")
    return updated


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _duplicate_keys(connection: sqlite3.Connection) -> list[tuple]:
    return connection.execute(
        """
        SELECT congress, chamber, vote_session, roll_number, COUNT(*)
        FROM votes
        GROUP BY congress, chamber, vote_session, roll_number
        HAVING COUNT(*) > 1
        LIMIT 20
        """
    ).fetchall()


def migrate_connection(connection: sqlite3.Connection) -> bool:
    """Apply the table rebuild. Return ``True`` when a change was made."""
    connection.execute("PRAGMA busy_timeout=30000")
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='votes'"
    ).fetchone()
    if not row or not row[0]:
        raise RuntimeError("votes table was not found")
    create_sql = row[0]
    if _has_session_constraint(create_sql):
        return False

    duplicates = _duplicate_keys(connection)
    if duplicates:
        raise RuntimeError(f"duplicate session-aware vote keys block migration: {duplicates}")

    columns = [row[1] for row in connection.execute("PRAGMA table_info(votes)")]
    if "vote_session" not in columns:
        raise RuntimeError("votes.vote_session column is missing")
    explicit_indexes = [
        row[0]
        for row in connection.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type='index' AND tbl_name='votes' AND sql IS NOT NULL
            ORDER BY name
            """
        )
        if row[0]
    ]

    updated_sql = _replace_constraint(create_sql)
    updated_sql, count = re.subn(
        r"\ACREATE\s+TABLE\s+(?:\"votes\"|votes)",
        f"CREATE TABLE {TEMP_TABLE}",
        updated_sql,
        count=1,
        flags=re.IGNORECASE,
    )
    if count != 1:
        raise RuntimeError("could not rewrite votes table name")

    quoted_columns = ", ".join(_quote_ident(column) for column in columns)
    prior_fk = int(connection.execute("PRAGMA foreign_keys").fetchone()[0])
    connection.commit()
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f"DROP TABLE IF EXISTS {TEMP_TABLE}")
        connection.execute(updated_sql)
        connection.execute(
            f"INSERT INTO {TEMP_TABLE} ({quoted_columns}) "
            f"SELECT {quoted_columns} FROM votes"
        )
        source_count = connection.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
        copied_count = connection.execute(
            f"SELECT COUNT(*) FROM {TEMP_TABLE}"
        ).fetchone()[0]
        if copied_count != source_count:
            raise RuntimeError(f"vote copy mismatch: source={source_count}, copied={copied_count}")
        connection.execute("DROP TABLE votes")
        connection.execute(f"ALTER TABLE {TEMP_TABLE} RENAME TO votes")
        for index_sql in explicit_indexes:
            connection.execute(index_sql)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute(f"PRAGMA foreign_keys={'ON' if prior_fk else 'OFF'}")

    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"foreign-key violations after vote migration: {violations[:20]}")
    final_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='votes'"
    ).fetchone()[0]
    if not _has_session_constraint(final_sql):
        raise RuntimeError("session-aware vote constraint was not installed")
    return True


def _database_path(db_url: str) -> Path:
    prefix = "sqlite:///"
    if not db_url.startswith(prefix):
        raise RuntimeError("this guarded migration only supports file-backed SQLite")
    raw_path = db_url[len(prefix):]
    if not raw_path or raw_path == ":memory:":
        raise RuntimeError("a file-backed SQLite URL is required")
    return Path(raw_path).expanduser().resolve()


def _backup(source: sqlite3.Connection, database_path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"{database_path.stem}-before-vote-session-{stamp}.db"
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
    return backup_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=os.getenv("WTP_DB_URL"))
    parser.add_argument("--backup-dir")
    args = parser.parse_args()
    if not args.db_url:
        raise SystemExit("--db-url or WTP_DB_URL is required")

    database_path = _database_path(args.db_url)
    if not database_path.is_file():
        raise SystemExit(f"database file does not exist: {database_path}")
    backup_dir = Path(args.backup_dir).resolve() if args.backup_dir else database_path.parent / "backups"

    connection = sqlite3.connect(database_path, timeout=30)
    try:
        current_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='votes'"
        ).fetchone()
        if current_sql and _has_session_constraint(current_sql[0]):
            print(json.dumps({"status": "already_current", "database": str(database_path)}))
            return 0
        backup_path = _backup(connection, database_path, backup_dir)
        changed = migrate_connection(connection)
        print(json.dumps({
            "status": "migrated" if changed else "already_current",
            "database": str(database_path),
            "backup": str(backup_path),
        }))
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())

