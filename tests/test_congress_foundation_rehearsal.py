import json
from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jobs.rehearse_congress_foundation import run, sqlite_path, staging_sqlite_path, validate_snapshots
from jobs.sync_congress_foundation import enabled
from models.committee_models import CommitteeMembership
from models.database import TrackedMember


def _write_snapshots(root: Path, *, people: int = 530, memberships: int = 500) -> None:
    legislators = []
    for index in range(people):
        chamber = "sen" if index < 100 else "rep"
        legislators.append({
            "id": {"bioguide": f"X{index:06d}"},
            "name": {"official_full": f"Member {index}"},
            "terms": [{"type": chamber, "state": "MD", "party": "Democrat"}],
        })
    committees = [{"thomas_id": f"HS{index:02d}", "type": "house", "name": f"Committee {index}"} for index in range(30)]
    membership_rows = [{"bioguide": f"X{index % people:06d}", "name": f"Member {index % people}"} for index in range(memberships)]
    (root / "legislators-current.yaml").write_text(yaml.safe_dump(legislators), encoding="utf-8")
    (root / "committees-current.yaml").write_text(yaml.safe_dump(committees), encoding="utf-8")
    (root / "committee-membership-current.yaml").write_text(yaml.safe_dump({"HS00": membership_rows}), encoding="utf-8")


def test_rehearsal_refuses_non_staging_or_non_sqlite_database(tmp_path):
    assert staging_sqlite_path(f"sqlite:///{tmp_path / 'federal-staging.db'}").name == "federal-staging.db"
    with pytest.raises(ValueError, match="staging"):
        staging_sqlite_path(f"sqlite:///{tmp_path / 'wethepeople.db'}")
    with pytest.raises(ValueError, match="SQLite"):
        staging_sqlite_path("postgresql://example/wethepeople_staging")
    assert sqlite_path(f"sqlite:///{tmp_path / 'wethepeople.db'}", require_staging=False).name == "wethepeople.db"


def test_scheduled_foundation_sync_requires_explicit_environment_gate():
    assert enabled("staging", "1")
    assert enabled("production", "1")
    assert not enabled("production", "0")
    assert not enabled("development", "1")
    assert not enabled("", "1")


def test_snapshot_validation_accepts_complete_bounded_current_roster(tmp_path):
    _write_snapshots(tmp_path)
    counts = validate_snapshots(tmp_path)
    assert counts == {
        "source_legislators": 530,
        "source_house": 430,
        "source_senate": 100,
        "source_committees": 30,
        "source_memberships": 500,
    }


def test_snapshot_validation_rejects_truncated_source_before_writes(tmp_path):
    _write_snapshots(tmp_path, people=20, memberships=10)
    with pytest.raises(ValueError, match="expected 500-600"):
        validate_snapshots(tmp_path)


def test_rehearsal_reconciles_departed_members_memberships_and_provenance(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    _write_snapshots(source_dir)
    db_url = f"sqlite:///{tmp_path / 'congress-staging.db'}"

    first = run(db_url, source_dir=source_dir)
    assert first["active_members"] == 530
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        session.add(TrackedMember(
            person_id="departed_member",
            bioguide_id="Z999999",
            display_name="Departed Member",
            chamber="house",
            state="MD",
            party="D",
            is_active=1,
        ))
        session.add(CommitteeMembership(
            committee_thomas_id="HS00",
            bioguide_id="Z999999",
            person_id="departed_member",
            role="member",
        ))
        session.commit()

    second = run(db_url, source_dir=source_dir)
    assert second["active_members"] == 530
    assert second["reconciliation"]["deactivated_members"] == 1
    assert second["reconciliation"]["removed_memberships"] == 1
    with Session() as session:
        departed = session.query(TrackedMember).filter_by(bioguide_id="Z999999").one()
        current = session.query(TrackedMember).filter_by(bioguide_id="X000000").one()
        assert departed.is_active == 0
        provenance = json.loads(current.claim_sources_json)
        assert provenance[0]["sha256"]
