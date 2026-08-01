import json
import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from models.database import Base


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONFIG = ROOT / "alembic-canonical.ini"


def _run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["WTP_CANONICAL_DB_URL"] = database_url
    environment["DISABLE_STARTUP_FETCH"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(CANONICAL_CONFIG), *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_canonical_baseline_upgrades_empty_sqlite_without_drift(tmp_path):
    database_path = tmp_path / "canonical.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    upgrade = _run_alembic(database_url, "upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr

    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert set(Base.metadata.tables) <= tables
    assert "alembic_version_canonical" in tables
    assert "alembic_version" not in tables

    drift = _run_alembic(database_url, "check")
    assert drift.returncode == 0, drift.stdout + drift.stderr
    assert "No new upgrade operations detected" in drift.stdout + drift.stderr


def test_canonical_postgresql_offline_sql_has_no_sqlite_only_ddl():
    result = _run_alembic("postgresql://migration:unused@localhost/staging", "upgrade", "head", "--sql")
    assert result.returncode == 0, result.stdout + result.stderr
    sql = (result.stdout + result.stderr).lower()
    assert "create table users" in sql
    assert "pragma" not in sql
    assert "virtual table" not in sql
    assert "fts5" not in sql


def test_canonical_graph_is_single_root_and_isolated_from_legacy():
    canonical = ScriptDirectory.from_config(Config(str(CANONICAL_CONFIG)))
    legacy = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    canonical_revisions = {item.revision for item in canonical.walk_revisions()}
    legacy_revisions = {item.revision for item in legacy.walk_revisions()}
    legacy_roots = {item.revision for item in legacy.walk_revisions() if item.down_revision is None}

    assert canonical.get_heads() == ["canonical_20260731"]
    assert canonical.get_bases() == ["canonical_20260731"]
    assert canonical_revisions.isdisjoint(legacy_revisions)
    assert legacy_roots == {"001_initial", "auth001", "ratelimit001"}


def test_identity_inventory_covers_every_canonical_user_foreign_key():
    inventory = json.loads((ROOT / "config" / "identity_data_inventory.json").read_text(encoding="utf-8"))
    assert inventory["canonical_identity"] == {"table": "users", "primary_key": "id"}
    entries = inventory["tables"]

    expected = {}
    for table in Base.metadata.tables.values():
        columns = {
            column.name
            for column in table.columns
            if any(foreign_key.target_fullname == "users.id" for foreign_key in column.foreign_keys)
        }
        if columns:
            expected[table.name] = columns

    missing = {
        table: sorted(columns - set(entries.get(table, {}).get("identity_columns", [])))
        for table, columns in expected.items()
        if columns - set(entries.get(table, {}).get("identity_columns", []))
    }
    assert not missing
    assert entries["discussion_posts"]["classification"] == "public_content"
    assert entries["discussion_reports"]["classification"] == "private_moderation"
    assert entries["solution_votes"]["classification"] == "private_ballot"
