"""Validate and idempotently load the single curated Phase 4 Watch fixture."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.database import Bill, SessionLocal, SourceDocument
from models.issue_models import Issue, Video, VideoBill, VideoIssue

VIDEO_ID = "housing-rent-why-rents-move"
ISSUE_SLUG = "housing-rent"
BILL_ID = "hr1-119"


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
    if len(videos) != 1:
        raise WatchFixtureValidationError("Fixture must contain exactly one curated video")
    item = videos[0]
    if item.get("video_id") != VIDEO_ID or item.get("issue_slug") != ISSUE_SLUG:
        raise WatchFixtureValidationError("Fixture identifiers exceed the reviewed Watch scope")
    if item.get("bill_ids") != [BILL_ID]:
        raise WatchFixtureValidationError("Fixture must link exactly the reviewed Housing & Rent bill")
    for field in ("creator_label", "caption", "transcript", "published_at"):
        if not item.get(field):
            raise WatchFixtureValidationError(f"{field} is required")
    _https(item.get("media_url"), "media_url")
    if item.get("captions_url"):
        _https(item["captions_url"], "captions_url")
    source = item.get("source") or {}
    _https(source.get("url"), "source.url")
    if not source.get("publisher") or not source.get("retrieved_at"):
        raise WatchFixtureValidationError("Source publisher and retrieved_at are required")
    _datetime(source["retrieved_at"])
    _datetime(item["published_at"])


def load_fixture(payload: dict[str, Any], session: Session) -> dict[str, int]:
    validate_fixture(payload)
    item = payload["videos"][0]
    issue = session.get(Issue, ISSUE_SLUG)
    bill = session.get(Bill, BILL_ID)
    if issue is None or bill is None:
        raise WatchFixtureValidationError("Load the complete Housing & Rent fixture first")

    source_data = item["source"]
    source = session.query(SourceDocument).filter_by(url=source_data["url"]).first()
    if source is None:
        source = SourceDocument(url=source_data["url"])
        session.add(source)
    source.publisher = source_data["publisher"]
    source.retrieved_at = _datetime(source_data["retrieved_at"])
    session.flush()

    video = session.get(Video, VIDEO_ID)
    if video is None:
        video = Video(video_id=VIDEO_ID)
        session.add(video)
    video.creator_label = item["creator_label"]
    video.caption = item["caption"]
    video.transcript = item["transcript"]
    video.captions_url = item.get("captions_url")
    video.media_url = item["media_url"]
    video.source = source
    video.published_at = _datetime(item["published_at"])
    video.sort_order = 0
    session.flush()

    if session.get(VideoIssue, (VIDEO_ID, ISSUE_SLUG)) is None:
        session.add(VideoIssue(video=video, issue=issue))
    if session.get(VideoBill, (VIDEO_ID, BILL_ID)) is None:
        session.add(VideoBill(video=video, bill=bill))
    session.commit()
    return {"videos": session.query(Video).count(), "video_issues": 1, "video_bills": 1}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        print(json.dumps(load_fixture(payload, session), sort_keys=True))


if __name__ == "__main__":
    main()
