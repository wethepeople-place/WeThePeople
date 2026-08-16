"""Load a human-reviewed official congressional office-contact fixture.

This loader performs no network requests. Operators must build the fixture from
official House/Senate sources, review it, and run it through a separately
approved migration/load gate.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from models.act_models import OfficialOfficeContact
from models.database import SessionLocal, TrackedMember


PHONE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
OFFICIAL_HOSTS = ("house.gov", "senate.gov", "congress.gov")
OFFICE_TYPES = {"washington", "district", "state", "contact_form"}


class ContactFixtureError(ValueError):
    pass


def _official_url(value: str, field: str) -> str:
    parsed = urlparse(str(value or "").strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(host == item or host.endswith(f".{item}") for item in OFFICIAL_HOSTS):
        raise ContactFixtureError(f"{field} must use an official House, Senate, or Congress HTTPS domain")
    return parsed.geturl()


def _timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContactFixtureError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ContactFixtureError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate(payload: dict, db: Session) -> list[dict]:
    if payload.get("schema_version") != 1 or not isinstance(payload.get("contacts"), list):
        raise ContactFixtureError("fixture must have schema_version 1 and a contacts list")
    output, seen = [], set()
    for index, raw in enumerate(payload["contacts"]):
        person_id = str(raw.get("person_id", "")).strip()
        if db.query(TrackedMember).filter_by(person_id=person_id, is_active=1).first() is None:
            raise ContactFixtureError(f"contacts[{index}] references an unknown active member")
        office_type = str(raw.get("office_type", "")).strip()
        if office_type not in OFFICE_TYPES:
            raise ContactFixtureError(f"contacts[{index}].office_type is invalid")
        phone = str(raw.get("phone", "")).strip() or None
        if phone and not PHONE.fullmatch(phone):
            raise ContactFixtureError(f"contacts[{index}].phone must be NNN-NNN-NNNN")
        contact_url = _official_url(raw["contact_url"], f"contacts[{index}].contact_url") if raw.get("contact_url") else None
        if not phone and not contact_url:
            raise ContactFixtureError(f"contacts[{index}] needs a public phone or official contact URL")
        item = {
            "person_id": person_id,
            "office_type": office_type,
            "label": str(raw.get("label", "")).strip(),
            "phone": phone,
            "contact_url": contact_url,
            "address": str(raw.get("address", "")).strip() or None,
            "source_url": _official_url(raw.get("source_url"), f"contacts[{index}].source_url"),
            "source_publisher": str(raw.get("source_publisher", "")).strip(),
            "retrieved_at": _timestamp(raw.get("retrieved_at"), f"contacts[{index}].retrieved_at"),
            "verified_at": _timestamp(raw.get("verified_at"), f"contacts[{index}].verified_at"),
        }
        if not item["label"] or not item["source_publisher"]:
            raise ContactFixtureError(f"contacts[{index}] needs label and source_publisher")
        # Mirror the loader's database identity. SQLite permits repeated NULL
        # values in UNIQUE constraints, so reject ambiguous contact-form rows.
        key = (person_id, office_type, phone)
        if key in seen:
            raise ContactFixtureError(f"contacts[{index}] duplicates another contact")
        seen.add(key); output.append(item)
    return output


def load_fixture(payload: dict, db: Session) -> dict:
    rows = validate(payload, db)
    active_keys = set()
    for item in rows:
        query = db.query(OfficialOfficeContact).filter_by(
            person_id=item["person_id"], office_type=item["office_type"], phone=item["phone"]
        )
        row = query.first()
        if row is None:
            row = OfficialOfficeContact(**item); db.add(row)
        else:
            for field, value in item.items(): setattr(row, field, value)
        row.verification_status = "verified"
        active_keys.add((item["person_id"], item["office_type"], item["phone"]))
    fixture_people = {item["person_id"] for item in rows}
    for row in db.query(OfficialOfficeContact).filter(OfficialOfficeContact.person_id.in_(fixture_people)).all():
        if (row.person_id, row.office_type, row.phone) not in active_keys:
            row.verification_status = "withdrawn"
    db.commit()
    return {"verified_contacts": len(rows), "members": len(fixture_people)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        print(json.dumps(load_fixture(payload, db), sort_keys=True))


if __name__ == "__main__":
    main()
