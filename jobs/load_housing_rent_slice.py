"""Validate and idempotently load a local Housing & Rent slice fixture."""

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from jobs.housing_rent_contract import CURATED_BILLS, EVIDENCE_SERIES, ISSUE_SLUG
from models.committee_models import Committee
from models.database import (
    Bill,
    BillAction,
    MemberBillGroundTruth,
    SessionLocal,
    SourceDocument,
)
from models.issue_models import (
    BillCommitteeReferral,
    EvidenceObservation,
    EvidenceSeries,
    Issue,
    IssueBill,
)


class SliceValidationError(ValueError):
    """The local fixture violates the reviewed Housing & Rent contract."""


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _require_source(source: dict[str, Any]) -> None:
    if not str(source.get("url", "")).startswith("https://"):
        raise SliceValidationError("Every source URL must use HTTPS")
    if not source.get("publisher") or not source.get("retrieved_at"):
        raise SliceValidationError("Every source requires publisher and retrieved_at")
    _datetime(source["retrieved_at"])


def validate_fixture(payload: dict[str, Any]) -> None:
    issue = payload.get("issue") or {}
    if issue.get("slug") != ISSUE_SLUG or not issue.get("title"):
        raise SliceValidationError(f"Fixture issue must be {ISSUE_SLUG!r} with a title")

    sources = payload.get("sources") or []
    if not sources:
        raise SliceValidationError("Fixture must declare normalized sources")
    for source in sources:
        _require_source(source)
    source_urls = {source["url"] for source in sources}
    if len(source_urls) != len(sources):
        raise SliceValidationError("Source URLs must be unique")

    series = payload.get("evidence_series") or []
    expected_series = {spec.key for spec in EVIDENCE_SERIES}
    if {item.get("key") for item in series} != expected_series:
        raise SliceValidationError("Fixture must contain exactly the two reviewed evidence series")
    for item in series:
        if item.get("source_url") not in source_urls or not item.get("observations"):
            raise SliceValidationError("Every evidence series needs a declared source and observations")
        for observation in item["observations"]:
            _date(observation["date"])
            float(observation["value"])
            if observation.get("source_url", item["source_url"]) not in source_urls:
                raise SliceValidationError("Every observation source must be declared")

    bills = payload.get("bills") or []
    expected_bills = {spec.bill_id for spec in CURATED_BILLS}
    if {item.get("bill_id") for item in bills} != expected_bills:
        raise SliceValidationError("Fixture must contain exactly the seven reviewed bills")
    for item in bills:
        if item.get("source_url") not in source_urls:
            raise SliceValidationError("Every bill needs a declared source")
        if item.get("phase") not in {"past", "current", "upcoming"}:
            raise SliceValidationError("Every issue-bill link needs a reviewed phase")
        for relationship in item.get("people", []):
            if relationship.get("role") not in {"sponsor", "cosponsor"}:
                raise SliceValidationError("Bill people roles must be sponsor or cosponsor")
            if not relationship.get("bioguide_id"):
                raise SliceValidationError("Bill people require canonical bioguide IDs")
        for referral in item.get("committee_referrals", []):
            if not referral.get("thomas_id") or referral.get("source_url") not in source_urls:
                raise SliceValidationError("Committee referrals require Thomas ID and declared source")
            _date(referral["referred_at"])


def _source(session: Session, source: dict[str, Any]) -> SourceDocument:
    row = session.query(SourceDocument).filter(SourceDocument.url == source["url"]).first()
    if row is None:
        row = SourceDocument(url=source["url"])
        session.add(row)
    row.publisher = source["publisher"]
    row.retrieved_at = _datetime(source["retrieved_at"])
    row.content_hash = source.get("content_hash")
    session.flush()
    return row


def _action_hash(bill_id: str, action_date: datetime, action_text: str) -> str:
    raw = f"{bill_id}|{action_date.isoformat()}|{action_text}".encode()
    return hashlib.sha256(raw).hexdigest()


def load_fixture(payload: dict[str, Any], session: Session) -> dict[str, int]:
    """Load a validated fixture and return stable post-load row counts."""

    validate_fixture(payload)
    sources = {_item["url"]: _source(session, _item) for _item in payload["sources"]}

    issue_data = payload["issue"]
    issue = session.get(Issue, ISSUE_SLUG)
    if issue is None:
        issue = Issue(slug=ISSUE_SLUG)
        session.add(issue)
    issue.title = issue_data["title"]
    issue.summary = issue_data.get("summary")
    session.flush()

    for item in payload["evidence_series"]:
        series = (
            session.query(EvidenceSeries)
            .filter_by(
                issue_slug=ISSUE_SLUG,
                key=item["key"],
                geography_type=item.get("geography_type", "national"),
                geography_id=item.get("geography_id", "US"),
            )
            .first()
        )
        if series is None:
            series = EvidenceSeries(issue=issue, key=item["key"])
            session.add(series)
        series.title = item["title"]
        series.unit = item["unit"]
        series.geography_type = item.get("geography_type", "national")
        series.geography_id = item.get("geography_id", "US")
        series.source = sources[item["source_url"]]
        session.flush()
        for obs in item["observations"]:
            observed = _date(obs["date"])
            row = (
                session.query(EvidenceObservation)
                .filter_by(series_id=series.id, observation_date=observed)
                .first()
            )
            if row is None:
                row = EvidenceObservation(series=series, observation_date=observed)
                session.add(row)
            row.value = float(obs["value"])
            row.source = sources[obs.get("source_url", item["source_url"])]
            row.source_record_id = obs.get("source_record_id")

    bill_specs = {spec.bill_id: spec for spec in CURATED_BILLS}
    for item in payload["bills"]:
        spec = bill_specs[item["bill_id"]]
        bill = session.get(Bill, spec.bill_id)
        if bill is None:
            bill = Bill(
                bill_id=spec.bill_id,
                congress=spec.congress,
                bill_type=spec.bill_type,
                bill_number=spec.bill_number,
            )
            session.add(bill)
        bill.title = item["title"]
        bill.policy_area = item.get("policy_area")
        bill.status_bucket = item["status_bucket"]
        bill.status_reason = item.get("status_reason")
        bill.latest_action_text = item.get("latest_action_text")
        bill.latest_action_date = _datetime(item["latest_action_date"]) if item.get("latest_action_date") else None
        bill.needs_enrichment = int(item.get("needs_enrichment", 1))
        session.flush()

        link = session.get(IssueBill, (ISSUE_SLUG, spec.bill_id))
        if link is None:
            link = IssueBill(issue=issue, bill=bill)
            session.add(link)
        link.phase = item["phase"]
        link.relevance_note = item.get("relevance_note")
        link.source = sources[item["source_url"]]

        for person in item.get("people", []):
            db_role = f"{person['role']}ed"
            relation = (
                session.query(MemberBillGroundTruth)
                .filter_by(bioguide_id=person["bioguide_id"], bill_id=spec.bill_id, role=db_role)
                .first()
            )
            if relation is None:
                relation = MemberBillGroundTruth(
                    bioguide_id=person["bioguide_id"], bill_id=spec.bill_id, role=db_role
                )
                session.add(relation)
            relation.source = person.get("source", "congress.gov.api.v3")
            relation.fetched_at = sources[item["source_url"]].retrieved_at

        for referral in item.get("committee_referrals", []):
            committee = session.query(Committee).filter_by(thomas_id=referral["thomas_id"]).first()
            if committee is None:
                committee = Committee(thomas_id=referral["thomas_id"])
                session.add(committee)
            committee.name = referral["name"]
            committee.chamber = referral["chamber"]
            committee.url = referral.get("official_url")

            action_date = _datetime(referral["action_date"])
            dedupe_hash = _action_hash(spec.bill_id, action_date, referral["action_text"])
            action = session.query(BillAction).filter_by(dedupe_hash=dedupe_hash).first()
            if action is None:
                action = BillAction(bill=bill, dedupe_hash=dedupe_hash)
                session.add(action)
            action.action_date = action_date
            action.action_text = referral["action_text"]
            action.action_code = referral.get("action_code")
            action.chamber = referral.get("chamber")
            action.committee = referral["name"]
            session.flush()

            referred_at = _date(referral["referred_at"])
            link = (
                session.query(BillCommitteeReferral)
                .filter_by(
                    bill_id=spec.bill_id,
                    committee_thomas_id=referral["thomas_id"],
                    referred_at=referred_at,
                )
                .first()
            )
            if link is None:
                link = BillCommitteeReferral(bill=bill, committee=committee, referred_at=referred_at)
                session.add(link)
            link.bill_action = action
            link.source = sources[referral["source_url"]]

    session.commit()
    return {
        "issues": session.query(Issue).filter_by(slug=ISSUE_SLUG).count(),
        "evidence_series": session.query(EvidenceSeries).filter_by(issue_slug=ISSUE_SLUG).count(),
        "evidence_observations": (
            session.query(EvidenceObservation)
            .join(EvidenceSeries)
            .filter(EvidenceSeries.issue_slug == ISSUE_SLUG)
            .count()
        ),
        "issue_bills": session.query(IssueBill).filter_by(issue_slug=ISSUE_SLUG).count(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="Path to a reviewed local JSON fixture")
    args = parser.parse_args()
    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        counts = load_fixture(payload, session)
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
