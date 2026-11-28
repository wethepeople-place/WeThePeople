"""Import official U.S. Senate roll-call XML files into the politics database.

The Senate LIS endpoints block the production datacenter, so GitHub Actions
downloads the public XML files and transfers them to the API container.  This
job performs only local parsing and database writes.

Usage:
    python jobs/import_senate_xml.py --source-dir /tmp/senate-votes \
        --congress 119 --session 2
"""

from __future__ import annotations

import argparse
import logging
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.database import MemberVote, SessionLocal, TrackedMember, Vote
from jobs.sync_senate_votes import build_senator_map, match_senator, normalize_position

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("import_senate_xml")


def _value(root: ET.Element, path: str, default: str = "") -> str:
    value = root.findtext(path)
    return value.strip() if value else default


def _integer(root: ET.Element | None, path: str, default: int = 0) -> int:
    if root is None:
        return default
    raw = _value(root, path)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _parse_vote_date(raw: str):
    for fmt in ("%B %d, %Y, %I:%M %p", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _bill_type(raw: str) -> str | None:
    normalized = raw.replace(".", "").replace(" ", "").upper()
    return normalized or None


def parse_vote_xml(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    congress = _integer(root, "congress")
    session = _integer(root, "session")
    roll = _integer(root, "vote_number")
    if not congress or not session or not roll:
        raise ValueError(f"{path.name}: missing congress/session/vote_number")

    document = root.find("document")
    document_number = _integer(document, "document_number") if document is not None else 0
    document_type = _bill_type(_value(document, "document_type")) if document is not None else None
    document_congress = _integer(document, "document_congress") if document is not None else 0

    voters = []
    for member in root.findall("./members/member"):
        first_name = _value(member, "first_name")
        last_name = _value(member, "last_name")
        voters.append(
            {
                "first_name": first_name,
                "last_name": last_name,
                "member_full": _value(member, "member_full") or f"{first_name} {last_name}".strip(),
                "party": _value(member, "party") or None,
                "state": _value(member, "state") or None,
                "vote_cast": _value(member, "vote_cast"),
                "lis_member_id": _value(member, "lis_member_id") or None,
            }
        )

    if not voters:
        raise ValueError(f"{path.name}: no member vote rows found")

    source_url = (
        "https://www.senate.gov/legislative/LIS/roll_call_votes/"
        f"vote{congress}{session}/vote_{congress}_{session}_{roll:05d}.htm"
    )
    return {
        "congress": congress,
        "session": session,
        "roll_number": roll,
        "question": _value(root, "vote_question_text") or _value(root, "question"),
        "vote_date": _parse_vote_date(_value(root, "vote_date")),
        "related_bill_congress": document_congress or None,
        "related_bill_type": document_type,
        "related_bill_number": document_number or None,
        "result": _value(root, "vote_result") or _value(root, "vote_result_text"),
        "yea_count": _integer(root, "./count/yeas"),
        "nay_count": _integer(root, "./count/nays"),
        "present_count": _integer(root, "./count/present"),
        "not_voting_count": _integer(root, "./count/absent"),
        "source_url": source_url,
        "metadata_json": {
            "source": "senate.gov",
            "majority_requirement": _value(root, "majority_requirement") or None,
            "vote_title": _value(root, "vote_title") or None,
            "vote_document_text": _value(root, "vote_document_text") or None,
            "vote_result_text": _value(root, "vote_result_text") or None,
        },
        "voters": voters,
    }


def upsert_vote(
    record: dict[str, Any],
    by_last_state: dict,
    by_full_name: dict,
    by_bioguide: dict,
) -> tuple[str, int, int]:
    db = SessionLocal()
    try:
        vote = (
            db.query(Vote)
            .filter(
                Vote.congress == record["congress"],
                Vote.chamber == "senate",
                Vote.vote_session == record["session"],
                Vote.roll_number == record["roll_number"],
            )
            .first()
        )
        action = "updated" if vote else "inserted"
        if vote is None:
            vote = Vote(
                congress=record["congress"],
                chamber="senate",
                vote_session=record["session"],
                roll_number=record["roll_number"],
            )
            db.add(vote)

        for field in (
            "question",
            "vote_date",
            "related_bill_congress",
            "related_bill_type",
            "related_bill_number",
            "result",
            "yea_count",
            "nay_count",
            "present_count",
            "not_voting_count",
            "source_url",
            "metadata_json",
        ):
            setattr(vote, field, record.get(field))

        db.flush()
        db.query(MemberVote).filter(MemberVote.vote_id == vote.id).delete(
            synchronize_session=False
        )

        active_senators = (
            db.query(TrackedMember)
            .filter(TrackedMember.is_active == 1, TrackedMember.chamber == "senate")
            .all()
        )
        person_to_bioguide = {
            member.person_id: member.bioguide_id
            for member in active_senators
            if member.bioguide_id
        }

        matched = 0
        for voter in record["voters"]:
            full_name = f'{voter["first_name"]} {voter["last_name"]}'.strip()
            person_id = match_senator(
                None,
                voter["last_name"],
                voter["state"] or "",
                full_name or voter["member_full"],
                by_last_state,
                by_full_name,
                by_bioguide,
            )
            if person_id:
                matched += 1
            db.add(
                MemberVote(
                    vote_id=vote.id,
                    person_id=person_id,
                    bioguide_id=person_to_bioguide.get(person_id),
                    position=normalize_position(voter["vote_cast"]),
                    member_name=full_name or voter["member_full"],
                    party=voter["party"],
                    state=voter["state"],
                )
            )

        db.commit()
        return action, len(record["voters"]), matched
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run(source_dir: Path, congress: int, session: int) -> int:
    files = sorted(source_dir.glob(f"vote_{congress}_{session}_*.xml"))
    if not files:
        log.error("No official Senate XML files found in %s", source_dir)
        return 1

    db = SessionLocal()
    try:
        by_last_state, by_full_name, by_bioguide = build_senator_map(db)
    finally:
        db.close()

    stats = {
        "files": len(files),
        "inserted": 0,
        "updated": 0,
        "failed": 0,
        "member_votes": 0,
        "matched_member_votes": 0,
    }
    for index, path in enumerate(files, start=1):
        try:
            record = parse_vote_xml(path)
            if record["congress"] != congress or record["session"] != session:
                raise ValueError(f"{path.name}: unexpected congress/session")
            action, member_votes, matched = upsert_vote(
                record, by_last_state, by_full_name, by_bioguide
            )
            stats[action] += 1
            stats["member_votes"] += member_votes
            stats["matched_member_votes"] += matched
        except Exception as exc:
            stats["failed"] += 1
            log.exception("Failed to import %s: %s", path.name, exc)
        if index % 25 == 0 or index == len(files):
            log.info("Official Senate XML progress %s/%s: %s", index, len(files), stats)

    log.info("Official Senate XML import complete: %s", stats)
    return 1 if stats["failed"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--congress", type=int, required=True)
    parser.add_argument("--session", type=int, required=True)
    args = parser.parse_args()
    return run(args.source_dir, args.congress, args.session)


if __name__ == "__main__":
    raise SystemExit(main())
