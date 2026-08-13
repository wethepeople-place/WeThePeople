"""Build and verify the current Congress foundation in an isolated staging DB.

This command deliberately refuses production and non-staging database names.
It downloads the bounded current snapshots maintained by
unitedstates/congress-legislators, validates their shape before any database
write, imports members/committees/memberships, and emits a reproducible report.
Votes and member actions are separate network jobs and run only after this
foundation passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jobs.import_congress_legislators import (
    bootstrap_tracked_members,
    import_committees,
    import_memberships,
)
from models.committee_models import Committee, CommitteeMembership
from models.database import Base, TrackedMember


SOURCE_ROOT = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main"
SOURCE_FILES = (
    "legislators-current.yaml",
    "committees-current.yaml",
    "committee-membership-current.yaml",
)
STATE_CODES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC AS GU MP PR VI".split()
)


def sqlite_path(db_url: str, *, require_staging: bool = True) -> Path:
    prefix = "sqlite:///"
    if not db_url.startswith(prefix):
        raise ValueError("Congress foundation import requires a SQLite database")
    raw = db_url[len(prefix):]
    path = Path(raw).expanduser().resolve()
    if require_staging and "staging" not in path.name.lower():
        raise ValueError("Congress rehearsal database filename must contain 'staging'")
    return path


def staging_sqlite_path(db_url: str) -> Path:
    return sqlite_path(db_url, require_staging=True)


def validate_snapshots(root: Path) -> dict[str, int]:
    legislators = yaml.safe_load((root / SOURCE_FILES[0]).read_text(encoding="utf-8")) or []
    committees = yaml.safe_load((root / SOURCE_FILES[1]).read_text(encoding="utf-8")) or []
    memberships = yaml.safe_load((root / SOURCE_FILES[2]).read_text(encoding="utf-8")) or {}

    bioguides: list[str] = []
    chamber_counts = {"house": 0, "senate": 0}
    invalid_states: list[str] = []
    for person in legislators:
        bioguide = (person.get("id") or {}).get("bioguide")
        terms = person.get("terms") or []
        term = terms[-1] if terms else {}
        chamber = {"rep": "house", "sen": "senate"}.get(term.get("type"))
        if bioguide:
            bioguides.append(bioguide)
        if chamber:
            chamber_counts[chamber] += 1
        state = term.get("state")
        if state and state not in STATE_CODES:
            invalid_states.append(state)

    membership_count = sum(len(rows or []) for rows in memberships.values())
    failures = []
    if not 500 <= len(legislators) <= 600:
        failures.append(f"expected 500-600 current legislators, found {len(legislators)}")
    if not 420 <= chamber_counts["house"] <= 450:
        failures.append(f"expected 420-450 House members/delegates, found {chamber_counts['house']}")
    if not 95 <= chamber_counts["senate"] <= 105:
        failures.append(f"expected 95-105 senators, found {chamber_counts['senate']}")
    if len(bioguides) != len(set(bioguides)) or len(bioguides) != len(legislators):
        failures.append("current roster has missing or duplicate Bioguide IDs")
    if invalid_states:
        failures.append(f"current roster has invalid state/territory codes: {sorted(set(invalid_states))}")
    if len(committees) < 30:
        failures.append(f"expected at least 30 top-level committees, found {len(committees)}")
    if membership_count < 500:
        failures.append(f"expected at least 500 committee memberships, found {membership_count}")
    if failures:
        raise ValueError("; ".join(failures))
    return {
        "source_legislators": len(legislators),
        "source_house": chamber_counts["house"],
        "source_senate": chamber_counts["senate"],
        "source_committees": len(committees),
        "source_memberships": membership_count,
    }


def download_snapshots(root: Path, transport=requests) -> list[dict[str, Any]]:
    sources = []
    for name in SOURCE_FILES:
        url = f"{SOURCE_ROOT}/{name}"
        response = transport.get(url, timeout=60)
        response.raise_for_status()
        payload = response.content
        (root / name).write_bytes(payload)
        sources.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)})
    return sources


def reconcile_current_snapshot(session, root: Path, sources: list[dict[str, Any]]) -> dict[str, int]:
    """Apply authoritative removals only after the complete snapshot passes validation."""
    legislators = yaml.safe_load((root / SOURCE_FILES[0]).read_text(encoding="utf-8")) or []
    memberships = yaml.safe_load((root / SOURCE_FILES[2]).read_text(encoding="utf-8")) or {}
    current_bioguides = {
        (person.get("id") or {}).get("bioguide")
        for person in legislators
        if (person.get("id") or {}).get("bioguide")
    }
    current_memberships = {
        (committee_id, member.get("bioguide"))
        for committee_id, rows in memberships.items()
        for member in (rows or [])
        if member.get("bioguide")
    }

    deactivated = (
        session.query(TrackedMember)
        .filter(TrackedMember.is_active == 1, TrackedMember.bioguide_id.notin_(current_bioguides))
        .update({TrackedMember.is_active: 0}, synchronize_session=False)
    )
    stale_memberships = [
        row for row in session.query(CommitteeMembership).all()
        if (row.committee_thomas_id, row.bioguide_id) not in current_memberships
    ]
    for row in stale_memberships:
        session.delete(row)

    roster_source = next(source for source in sources if source["url"].endswith(SOURCE_FILES[0]))
    provenance = json.dumps([{
        "url": roster_source["url"],
        "type": "public-identity-index",
        "sha256": roster_source["sha256"],
    }], separators=(",", ":"), sort_keys=True)
    provenance_updates = (
        session.query(TrackedMember)
        .filter(TrackedMember.bioguide_id.in_(current_bioguides))
        .update({TrackedMember.claim_sources_json: provenance}, synchronize_session=False)
    )
    session.commit()
    return {
        "deactivated_members": deactivated,
        "removed_memberships": len(stale_memberships),
        "provenance_updates": provenance_updates,
    }


def run(
    db_url: str,
    *,
    source_dir: Path | None = None,
    allow_non_staging: bool = False,
) -> dict[str, Any]:
    db_path = sqlite_path(db_url, require_staging=not allow_non_staging)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="wtp-congress-") if source_dir is None else None
    root = source_dir or Path(temporary.name)
    try:
        sources = download_snapshots(root) if source_dir is None else [
            {
                "url": f"local:{name}",
                "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                "bytes": (root / name).stat().st_size,
            }
            for name in SOURCE_FILES
        ]
        source_counts = validate_snapshots(root)
        engine = create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 60})
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            member_changes = bootstrap_tracked_members(session, str(root))
            committee_changes = import_committees(session, str(root))
            membership_changes = import_memberships(session, str(root))
            reconciliation = reconcile_current_snapshot(session, root, sources)
            active_members = session.query(TrackedMember).filter(TrackedMember.is_active == 1).count()
            committee_count = session.query(Committee).count()
            membership_count = session.query(CommitteeMembership).count()
            linked_count = session.query(CommitteeMembership).filter(CommitteeMembership.person_id.isnot(None)).count()
        if active_members != source_counts["source_legislators"]:
            raise RuntimeError(f"active member reconciliation failed: source={source_counts['source_legislators']} db={active_members}")
        if membership_count and linked_count / membership_count < 0.98:
            raise RuntimeError(f"committee membership linkage below 98%: {linked_count}/{membership_count}")
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "database": str(db_path),
            "sources": sources,
            **source_counts,
            "member_changes": member_changes,
            "committee_changes": committee_changes,
            "membership_changes": membership_changes,
            "reconciliation": reconciliation,
            "active_members": active_members,
            "committees": committee_count,
            "memberships": membership_count,
            "linked_memberships": linked_count,
        }
    finally:
        if temporary is not None:
            temporary.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run(args.db_url, source_dir=args.source_dir)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
