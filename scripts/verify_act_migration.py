"""Verify a disposable ACT canonical migration database."""

import sqlite3
import sys
from pathlib import Path


EXPECTED = {
    "official_office_contacts",
    "act_receipts",
    "action_circles",
    "action_circle_memberships",
    "civic_activities",
    "civic_activity_rsvps",
}


def verify(path: Path) -> dict:
    with sqlite3.connect(path) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        revision = db.execute("SELECT version_num FROM alembic_version_canonical").fetchone()[0]
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = sorted(EXPECTED - tables)
    if integrity != "ok" or revision != "canonical_act_foundation_001" or missing:
        raise RuntimeError({"integrity": integrity, "revision": revision, "missing": missing})
    return {"integrity": integrity, "revision": revision, "tables": sorted(EXPECTED)}


if __name__ == "__main__":
    print(verify(Path(sys.argv[1])))
