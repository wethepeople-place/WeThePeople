"""Load one reviewed Housing & Rent citizen solution without network calls."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.auth_models import User
from models.civic_models import Proposal, SolutionRevision
from models.database import SessionLocal
from models.issue_models import Issue
from models.social_models import DiscussionAttachment, DiscussionPost

ISSUE_SLUG = "housing-rent"
TITLE = "Pilot faster rental assistance delivery"
DISCUSSION_BODY = "What should Congress prioritize first to make rent more affordable? Start with the evidence, then explain the tradeoff behind your answer."


class SolutionFixtureValidationError(ValueError):
    pass


def validate_fixture(payload: dict[str, Any]) -> None:
    items = payload.get("solutions") or []
    if len(items) != 1:
        raise SolutionFixtureValidationError("Fixture must contain exactly one reviewed solution")
    item = items[0]
    if item.get("issue_slug") != ISSUE_SLUG or item.get("title") != TITLE:
        raise SolutionFixtureValidationError("Fixture exceeds the reviewed Housing & Rent scope")
    if item.get("discussion_body") != DISCUSSION_BODY:
        raise SolutionFixtureValidationError("Fixture must connect to the reviewed discussion")
    for field, minimum in (("summary", 10), ("body", 20), ("change_note", 3)):
        if len(str(item.get(field) or "").strip()) < minimum:
            raise SolutionFixtureValidationError(f"Fixture {field} is incomplete")


def load_fixture(payload: dict[str, Any], session: Session, creator_user_id: int) -> dict[str, int]:
    validate_fixture(payload)
    item = payload["solutions"][0]
    if session.get(User, creator_user_id) is None:
        raise SolutionFixtureValidationError("Creator must be an existing canonical user")
    if session.get(Issue, ISSUE_SLUG) is None:
        raise SolutionFixtureValidationError("Load the Housing & Rent fixture first")
    discussion = session.query(DiscussionPost).filter_by(body=DISCUSSION_BODY, moderation_status="published").first()
    if discussion is None:
        raise SolutionFixtureValidationError("Load the reviewed discussion fixture first")

    row = session.query(Proposal).filter_by(issue_slug=ISSUE_SLUG, title=TITLE).first()
    if row is None:
        row = Proposal(author_id=creator_user_id, issue_slug=ISSUE_SLUG, title=TITLE, summary=item["summary"],
                       body=item["body"], status="published", published_at=datetime.now(timezone.utc), latest_revision_number=1)
        session.add(row)
        session.flush()
        session.add(SolutionRevision(solution_id=row.id, editor_user_id=creator_user_id, revision_number=1,
                                     title=row.title, summary=row.summary, body=row.body, change_note=item["change_note"]))
    attachment = session.query(DiscussionAttachment).filter_by(post_id=discussion.id, attachment_type="solution").first()
    if attachment is None:
        attachment = DiscussionAttachment(post_id=discussion.id, attachment_type="solution", solution_id=row.id, label=row.title)
        session.add(attachment)
    session.commit()
    return {"solutions": 1, "revisions": 1, "discussion_attachments": 1}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--creator-user-id", type=int, required=True)
    args = parser.parse_args()
    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        print(json.dumps(load_fixture(payload, session, args.creator_user_id), sort_keys=True))


if __name__ == "__main__":
    main()
