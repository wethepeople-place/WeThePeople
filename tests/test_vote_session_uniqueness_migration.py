import importlib.util
import sqlite3
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "jobs" / "migrate_vote_session_uniqueness.py"
SPEC = importlib.util.spec_from_file_location("vote_session_migration", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _legacy_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        """
        CREATE TABLE votes (
            id INTEGER NOT NULL PRIMARY KEY,
            congress INTEGER NOT NULL,
            chamber VARCHAR NOT NULL,
            roll_number INTEGER NOT NULL,
            vote_session INTEGER,
            question TEXT,
            CONSTRAINT uq_votes_congress_chamber_roll
                UNIQUE (congress, chamber, roll_number)
        );
        CREATE INDEX ix_votes_chamber ON votes (chamber);
        CREATE TABLE member_votes (
            id INTEGER NOT NULL PRIMARY KEY,
            vote_id INTEGER NOT NULL REFERENCES votes(id) ON DELETE CASCADE
        );
        INSERT INTO votes VALUES (1, 119, 'house', 10, 1, '2025 vote');
        INSERT INTO votes VALUES (2, 119, 'house', 11, 2, '2026 vote');
        INSERT INTO member_votes VALUES (1, 1);
        """
    )
    connection.commit()
    return connection


def test_migration_allows_same_roll_in_different_sessions(tmp_path):
    connection = _legacy_database(tmp_path / "politics.db")

    assert MODULE.migrate_connection(connection) is True
    connection.execute(
        "INSERT INTO votes VALUES (3, 119, 'house', 10, 2, '2026 same roll')"
    )
    connection.commit()

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO votes VALUES (4, 119, 'house', 10, 2, 'duplicate')"
        )
    connection.rollback()
    assert connection.execute("SELECT COUNT(*) FROM member_votes").fetchone()[0] == 1
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert connection.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name='ix_votes_chamber'"
    ).fetchone()[0] == 1


def test_migration_is_idempotent(tmp_path):
    connection = _legacy_database(tmp_path / "politics.db")
    assert MODULE.migrate_connection(connection) is True
    assert MODULE.migrate_connection(connection) is False

