from pathlib import Path

import pytest
import yaml

from jobs.rehearse_congress_foundation import staging_sqlite_path, validate_snapshots


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
