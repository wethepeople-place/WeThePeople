import os
import sqlite3
import subprocess
import sys

from fastapi import HTTPException
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from models.database import Base
from routers import politics_committees


def test_documented_database_module_command_creates_committee_tables(tmp_path):
    database_path = tmp_path / "module-command.db"
    environment = os.environ.copy()
    environment["WTP_DB_URL"] = f"sqlite:///{database_path.as_posix()}"

    subprocess.run(
        [sys.executable, "-m", "models.database"],
        check=True,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=environment,
        capture_output=True,
        text=True,
    )

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"committees", "committee_memberships"} <= table_names


def test_fresh_database_creates_committee_tables_and_routes_are_safe(tmp_path, monkeypatch):
    database_path = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{database_path}")

    Base.metadata.create_all(bind=engine)

    table_names = set(inspect(engine).get_table_names())
    assert {"committees", "committee_memberships"} <= table_names

    TestSession = sessionmaker(bind=engine)
    monkeypatch.setattr(politics_committees, "SessionLocal", TestSession)

    assert politics_committees.list_committees(
        chamber=None,
        include_subcommittees=False,
    ) == {
        "total": 0,
        "committees": [],
    }

    try:
        politics_committees.get_committee_detail("HSBA")
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Committee HSBA not found"
    else:
        raise AssertionError("Missing committee detail must return HTTP 404")
