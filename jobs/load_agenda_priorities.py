"""Validate and idempotently load the reviewed AP-NORC 2026 Agenda fixture."""

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.database import SessionLocal, SourceDocument
from models.issue_models import Issue


AGENDA_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "agenda_2026_apnorc.json"
EXPECTED_PUBLISHER = "AP-NORC Center for Public Affairs Research"
EXPECTED_ITEM_COUNT = 20
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class AgendaFixtureValidationError(ValueError):
    """The reviewed priority fixture violates the bounded Agenda contract."""


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def validate_fixture(payload: dict[str, Any]) -> None:
    methodology = payload.get("methodology") or {}
    if methodology.get("kind") != "public_priorities_poll":
        raise AgendaFixtureValidationError("Agenda fixture must use the public priorities poll method")
    if methodology.get("publisher") != EXPECTED_PUBLISHER:
        raise AgendaFixtureValidationError("Agenda fixture publisher is outside the reviewed scope")
    for key in ("source_url", "topline_url"):
        if not str(methodology.get(key, "")).startswith("https://"):
            raise AgendaFixtureValidationError(f"Agenda {key} must use HTTPS")
    if int(methodology.get("sample_size", 0)) != 1146:
        raise AgendaFixtureValidationError("Agenda sample size must match the reviewed topline")
    if float(methodology.get("margin_of_error_points", 0)) != 4.0:
        raise AgendaFixtureValidationError("Agenda margin of error must match the reviewed topline")
    if date.fromisoformat(methodology.get("survey_start", "")) > date.fromisoformat(
        methodology.get("survey_end", "")
    ):
        raise AgendaFixtureValidationError("Agenda survey dates are reversed")
    _datetime(methodology.get("retrieved_at", ""))

    items = payload.get("items") or []
    if len(items) != EXPECTED_ITEM_COUNT:
        raise AgendaFixtureValidationError("Agenda fixture must contain exactly 20 issues")
    if [item.get("rank") for item in items] != list(range(1, EXPECTED_ITEM_COUNT + 1)):
        raise AgendaFixtureValidationError("Agenda ranks must be contiguous from 1 through 20")
    slugs = [item.get("slug") for item in items]
    if len(set(slugs)) != EXPECTED_ITEM_COUNT or not all(
        isinstance(slug, str) and SLUG_PATTERN.fullmatch(slug) for slug in slugs
    ):
        raise AgendaFixtureValidationError("Agenda issue slugs must be unique and canonical")
    shares = [item.get("priority_share") for item in items]
    if not all(isinstance(value, int) and 0 <= value <= 100 for value in shares):
        raise AgendaFixtureValidationError("Agenda priority shares must be whole percentages")
    if shares != sorted(shares, reverse=True):
        raise AgendaFixtureValidationError("Agenda priority shares must be non-increasing")
    if not all(item.get("title") and item.get("summary") for item in items):
        raise AgendaFixtureValidationError("Every Agenda issue requires a title and summary")


def load_fixture(payload: dict[str, Any], session: Session) -> dict[str, int]:
    """Upsert only the reviewed issue identities; never seed evidence or engagement."""

    validate_fixture(payload)
    methodology = payload["methodology"]
    source = (
        session.query(SourceDocument)
        .filter(SourceDocument.url == methodology["topline_url"])
        .first()
    )
    if source is None:
        source = SourceDocument(url=methodology["topline_url"])
        session.add(source)
    source.publisher = methodology["publisher"]
    source.retrieved_at = _datetime(methodology["retrieved_at"])

    created = 0
    for item in payload["items"]:
        issue = session.get(Issue, item["slug"])
        if issue is None:
            issue = Issue(slug=item["slug"], summary=item["summary"])
            session.add(issue)
            created += 1
        issue.title = item["title"]
        # Preserve richer reviewed summaries already attached to an issue hub.
        if not issue.summary:
            issue.summary = item["summary"]

    session.commit()
    slugs = [item["slug"] for item in payload["items"]]
    return {
        "agenda_issues": session.query(Issue).filter(Issue.slug.in_(slugs)).count(),
        "created": created,
        "sources": session.query(SourceDocument).filter_by(url=methodology["topline_url"]).count(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=AGENDA_FIXTURE_PATH)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Required acknowledgement that the validated fixture should be written",
    )
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing to write without --apply")
    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        print(json.dumps(load_fixture(payload, session), sort_keys=True))


if __name__ == "__main__":
    main()
