"""Validate and idempotently load the bounded development Watch fixture."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.database import Bill, SessionLocal, SourceDocument
from models.issue_models import Issue, IssueBill, Video, VideoBill, VideoIssue

ISSUE_SLUG = "housing-rent"
LEGACY_BILL_ID = "hr1-119"
ROAD_ACT_BILL_ID = "hr6644-119"
ALLOWED_BILL_IDS = {LEGACY_BILL_ID, ROAD_ACT_BILL_ID}
REPLACED_VIDEO_IDS = {
    "housing-rent-why-rents-move",
    "housing-rent-evidence-first",
    "housing-rent-follow-the-bill",
}
DELIVERY_MODES = {"official_embed", "hosted_video", "link_out"}


class WatchFixtureValidationError(ValueError):
    pass


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _https(value: Any, field: str) -> str:
    text = str(value or "")
    if not text.startswith("https://"):
        raise WatchFixtureValidationError(f"{field} must use HTTPS")
    return text


def validate_fixture(payload: dict[str, Any]) -> None:
    videos = payload.get("videos") or []
    if not 1 <= len(videos) <= 5:
        raise WatchFixtureValidationError("Fixture must contain one to five bounded development videos")
    ids = [item.get("video_id") for item in videos]
    if any(not value for value in ids) or len(set(ids)) != len(ids):
        raise WatchFixtureValidationError("Fixture video identifiers must be present and unique")
    for item in videos:
        if item.get("issue_slug") != ISSUE_SLUG:
            raise WatchFixtureValidationError("Fixture identifiers exceed the reviewed Watch scope")
        if not isinstance(item.get("bill_ids"), list) or len(item["bill_ids"]) != 1 or item["bill_ids"][0] not in ALLOWED_BILL_IDS:
            raise WatchFixtureValidationError("Fixture must link exactly the reviewed Housing & Rent bill")
        for field in ("creator_label", "caption", "transcript", "published_at"):
            if not item.get(field):
                raise WatchFixtureValidationError(f"{field} is required")
        _https(item.get("media_url"), "media_url")
        if item.get("captions_url"):
            _https(item["captions_url"], "captions_url")
        delivery = item.get("delivery")
        if delivery is not None:
            if delivery.get("mode") not in DELIVERY_MODES:
                raise WatchFixtureValidationError("delivery.mode is not supported")
            _https(delivery.get("canonical_url"), "delivery.canonical_url")
            if delivery["mode"] == "official_embed":
                for field in ("provider", "provider_video_id", "source_label"):
                    if not delivery.get(field):
                        raise WatchFixtureValidationError(f"delivery.{field} is required for official_embed")
                if delivery.get("development_only") is not True:
                    raise WatchFixtureValidationError("Fixture official embeds must remain development_only")
        accessibility = item.get("accessibility")
        if accessibility is not None:
            if accessibility.get("text_kind") not in {"overview", "transcript"}:
                raise WatchFixtureValidationError("accessibility.text_kind is not supported")
            _https(accessibility.get("official_transcript_url"), "accessibility.official_transcript_url")
            if not accessibility.get("official_transcript_label"):
                raise WatchFixtureValidationError("accessibility.official_transcript_label is required")
            if accessibility.get("development_only") is not True:
                raise WatchFixtureValidationError("Fixture accessibility metadata must remain development_only")
        source = item.get("source") or {}
        _https(source.get("url"), "source.url")
        if not source.get("publisher") or not source.get("retrieved_at"):
            raise WatchFixtureValidationError("Source publisher and retrieved_at are required")
        _datetime(source["retrieved_at"])
        _datetime(item["published_at"])


def load_fixture(payload: dict[str, Any], session: Session, *, replace_reviewed_catalog: bool = False) -> dict[str, int]:
    validate_fixture(payload)
    issue = session.get(Issue, ISSUE_SLUG)
    if issue is None:
        raise WatchFixtureValidationError("Load the complete Housing & Rent fixture first")

    desired_ids = {item["video_id"] for item in payload["videos"]}
    if replace_reviewed_catalog:
        current_ids = {value for value, in session.query(Video.video_id).all()}
        allowed_current = REPLACED_VIDEO_IDS | desired_ids
        if not current_ids <= allowed_current:
            raise WatchFixtureValidationError("Production catalog contains videos outside the exact reviewed replacement scope")
        removed = current_ids - desired_ids
        if removed:
            session.query(VideoBill).filter(VideoBill.video_id.in_(removed)).delete(synchronize_session=False)
            session.query(VideoIssue).filter(VideoIssue.video_id.in_(removed)).delete(synchronize_session=False)
            session.query(Video).filter(Video.video_id.in_(removed)).delete(synchronize_session=False)

    for sort_order, item in enumerate(payload["videos"]):
        bill_id = item["bill_ids"][0]
        bill = session.get(Bill, bill_id)
        if bill is None and bill_id == ROAD_ACT_BILL_ID:
            bill = Bill(
                bill_id=ROAD_ACT_BILL_ID,
                congress=119,
                bill_type="hr",
                bill_number=6644,
                title="21st Century ROAD to Housing Act",
                policy_area="Housing and Community Development",
                status_bucket="became_law",
                status_reason="Became Public Law 119-101 without presidential signature",
                latest_action_text="Became Public Law No: 119-101.",
                latest_action_date=_datetime("2026-07-11T00:00:00Z"),
                needs_enrichment=0,
                full_text_url="https://www.govinfo.gov/app/details/BILLS-119hr6644enr",
            )
            session.add(bill)
            session.flush()
        if bill is None:
            raise WatchFixtureValidationError("Load the complete Housing & Rent fixture first")
        if bill_id == ROAD_ACT_BILL_ID and session.get(IssueBill, (ISSUE_SLUG, bill_id)) is None:
            evidence_url = "https://www.govinfo.gov/app/details/BILLS-119hr6644enr"
            evidence_source = session.query(SourceDocument).filter_by(url=evidence_url).first()
            if evidence_source is None:
                evidence_source = SourceDocument(url=evidence_url, publisher="U.S. Government Publishing Office", retrieved_at=_datetime("2026-08-11T00:00:00Z"))
                session.add(evidence_source)
                session.flush()
            session.add(IssueBill(
                issue=issue,
                bill=bill,
                phase="enacted",
                relevance_note="The enacted law addresses housing supply, affordability, financing, homeownership, and federal housing programs.",
                source_id=evidence_source.id,
            ))
        source_data = item["source"]
        source = session.query(SourceDocument).filter_by(url=source_data["url"]).first()
        if source is None:
            source = SourceDocument(url=source_data["url"])
            session.add(source)
        source.publisher = source_data["publisher"]
        source.retrieved_at = _datetime(source_data["retrieved_at"])
        session.flush()
        video = session.get(Video, item["video_id"])
        if video is None:
            video = Video(video_id=item["video_id"])
            session.add(video)
        video.creator_label = item["creator_label"]
        video.caption = item["caption"]
        video.transcript = item["transcript"]
        video.captions_url = item.get("captions_url")
        video.media_url = item["media_url"]
        video.source = source
        video.published_at = _datetime(item["published_at"])
        video.sort_order = sort_order
        session.flush()
        if session.get(VideoIssue, (video.video_id, ISSUE_SLUG)) is None:
            session.add(VideoIssue(video=video, issue=issue))
        session.query(VideoBill).filter(VideoBill.video_id == video.video_id, VideoBill.bill_id != bill_id).delete(synchronize_session=False)
        if session.get(VideoBill, (video.video_id, bill_id)) is None:
            session.add(VideoBill(video=video, bill=bill))
    session.commit()
    count = len(payload["videos"])
    return {"videos": session.query(Video).count(), "video_issues": count, "video_bills": count}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--replace-reviewed-catalog", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        print(json.dumps(load_fixture(payload, session, replace_reviewed_catalog=args.replace_reviewed_catalog), sort_keys=True))


if __name__ == "__main__":
    main()
