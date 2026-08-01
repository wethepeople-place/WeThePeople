"""Load the single reviewed Housing & Rent discussion thread without network calls."""

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.database import Bill, SessionLocal, SourceDocument
from models.issue_models import Issue, Video
from models.social_models import DiscussionAttachment, DiscussionPost

THREAD_BODY = "What should Congress prioritize first to make rent more affordable? Start with the evidence, then explain the tradeoff behind your answer."
VIDEO_ID = "housing-rent-why-rents-move"
ISSUE_SLUG = "housing-rent"
BILL_ID = "hr1-119"


class DiscussFixtureValidationError(ValueError):
    pass


def validate_fixture(payload: dict[str, Any]) -> None:
    threads = payload.get("threads") or []
    if len(threads) != 1:
        raise DiscussFixtureValidationError("Fixture must contain exactly one curated thread")
    item = threads[0]
    if item.get("body") != THREAD_BODY:
        raise DiscussFixtureValidationError("Fixture body must match the reviewed prompt")
    if item.get("video_id") != VIDEO_ID or item.get("issue_slug") != ISSUE_SLUG:
        raise DiscussFixtureValidationError("Fixture exceeds the reviewed Watch/issue scope")
    if item.get("bill_id") != BILL_ID or item.get("author_label") != "WeThePeople.place":
        raise DiscussFixtureValidationError("Fixture bill or editorial author is invalid")
    source_url = str(item.get("source_url") or "")
    if not source_url.startswith("https://"):
        raise DiscussFixtureValidationError("Fixture source must use HTTPS")


def load_fixture(payload: dict[str, Any], session: Session) -> dict[str, int]:
    validate_fixture(payload)
    item = payload["threads"][0]
    video = session.get(Video, VIDEO_ID)
    issue = session.get(Issue, ISSUE_SLUG)
    bill = session.get(Bill, BILL_ID)
    source = session.query(SourceDocument).filter_by(url=item["source_url"]).first()
    if not all((video, issue, bill, source)):
        raise DiscussFixtureValidationError("Load the complete Housing & Rent and Watch fixtures first")

    post = session.query(DiscussionPost).filter_by(author_id=None, body=THREAD_BODY).first()
    if post is None:
        post = DiscussionPost(author_label="WeThePeople.place", body=THREAD_BODY)
        session.add(post)
        session.flush()

    targets = (
        ("video", "video_id", video.video_id, "Watch: Housing & Rent"),
        ("issue", "issue_slug", issue.slug, issue.title),
        ("bill", "bill_id", bill.bill_id, bill.title),
        ("source", "source_id", source.id, source.publisher),
    )
    for kind, field, value, label in targets:
        row = session.query(DiscussionAttachment).filter_by(post_id=post.id, attachment_type=kind).first()
        if row is None:
            row = DiscussionAttachment(post_id=post.id, attachment_type=kind)
            session.add(row)
        setattr(row, field, value)
        row.label = label
    session.commit()
    return {"threads": 1, "attachments": 4}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        print(json.dumps(load_fixture(payload, session), sort_keys=True))


if __name__ == "__main__":
    main()
