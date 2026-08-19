"""Load or remove fictional discussion content in a disposable local database.

This loader is deliberately separate from the reviewed discussion fixture. Its
records are synthetic visual-test data and must never be loaded in production.
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.auth_models import User
from models.database import SessionLocal
from models.issue_models import Issue, Video
from models.social_models import (
    DiscussionAttachment,
    DiscussionBookmark,
    DiscussionPost,
    DiscussionReaction,
    DiscussionReply,
)
from utils.db_compat import DATABASE_URL

DEMO_EMAIL_PREFIX = "demo.discussion."
DEMO_EMAIL_SUFFIX = "@example.invalid"
DEMO_LABEL_SUFFIX = " (Demo)"
ALLOWED_VIDEO_IDS = {
    "housing-rent-road-act-explained",
    "housing-rent-road-act-becomes-law",
    "housing-rent-road-act-speaker",
}


class DiscussionDemoError(ValueError):
    pass


def assert_local_demo_environment(env: dict[str, str] | None = None, database_url: str | None = None) -> None:
    values = env or os.environ
    url = database_url or DATABASE_URL
    if values.get("WTP_DATA_CLASSIFICATION") != "synthetic":
        raise DiscussionDemoError("WTP_DATA_CLASSIFICATION must be synthetic")
    if values.get("WTP_TARGET_ENV") not in {"local", "development", "test"}:
        raise DiscussionDemoError("WTP_TARGET_ENV must be local, development, or test")
    if not url.startswith("sqlite:///"):
        raise DiscussionDemoError("Synthetic discussion demos require a file-backed SQLite database")
    path = url.removeprefix("sqlite:///").lower()
    if "demo" not in path and "synthetic" not in path:
        raise DiscussionDemoError("SQLite filename must contain demo or synthetic")


def validate_fixture(payload: dict[str, Any]) -> None:
    if payload.get("classification") != "synthetic" or payload.get("dataset") != "wtp-discussion-demo-v1":
        raise DiscussionDemoError("Fixture must declare the approved synthetic dataset")
    users = payload.get("users") or []
    posts = payload.get("posts") or []
    if not (5 <= len(users) <= 8 and 8 <= len(posts) <= 14):
        raise DiscussionDemoError("Fixture must remain bounded to 5-8 users and 8-14 posts")
    handles = {item.get("handle") for item in users}
    if len(handles) != len(users) or any(not str(item.get("display_name", "")).endswith(DEMO_LABEL_SUFFIX) for item in users):
        raise DiscussionDemoError("Every fictional user needs a unique handle and Demo label")
    for item in posts:
        if item.get("author") not in handles or item.get("issue_slug") != "housing-rent":
            raise DiscussionDemoError("Every post must use a fictional author and the reviewed issue")
        if item.get("video_id") and item["video_id"] not in ALLOWED_VIDEO_IDS:
            raise DiscussionDemoError("Post references an unapproved video")
        if not str(item.get("body", "")).strip().endswith("[Demo discussion]"):
            raise DiscussionDemoError("Every synthetic post must carry its visible demo marker")
        for reply in item.get("replies") or []:
            if reply.get("author") not in handles or not str(reply.get("body", "")).strip():
                raise DiscussionDemoError("Replies must use fictional authors and non-empty copy")


def _demo_users(session: Session) -> list[User]:
    return session.query(User).filter(
        User.email.like(f"{DEMO_EMAIL_PREFIX}%{DEMO_EMAIL_SUFFIX}")
    ).all()


def clear_fixture(session: Session, *, classification: str) -> dict[str, int]:
    if classification != "synthetic":
        raise DiscussionDemoError("Explicit synthetic classification is required")
    users = _demo_users(session)
    user_ids = [item.id for item in users]
    posts = session.query(DiscussionPost).filter(DiscussionPost.author_id.in_(user_ids)).all() if user_ids else []
    post_ids = [item.id for item in posts]
    if post_ids:
        session.query(DiscussionBookmark).filter(DiscussionBookmark.post_id.in_(post_ids)).delete(synchronize_session=False)
        session.query(DiscussionReaction).filter(
            DiscussionReaction.target_type == "post", DiscussionReaction.target_id.in_(post_ids)
        ).delete(synchronize_session=False)
        session.query(DiscussionReply).filter(DiscussionReply.post_id.in_(post_ids)).delete(synchronize_session=False)
        session.query(DiscussionAttachment).filter(DiscussionAttachment.post_id.in_(post_ids)).delete(synchronize_session=False)
        session.query(DiscussionPost).filter(DiscussionPost.id.in_(post_ids)).delete(synchronize_session=False)
    if user_ids:
        session.query(DiscussionReaction).filter(DiscussionReaction.user_id.in_(user_ids)).delete(synchronize_session=False)
        session.query(DiscussionBookmark).filter(DiscussionBookmark.user_id.in_(user_ids)).delete(synchronize_session=False)
        session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    session.commit()
    return {"users_removed": len(user_ids), "posts_removed": len(post_ids)}


def load_fixture(payload: dict[str, Any], session: Session, *, classification: str) -> dict[str, int]:
    if classification != "synthetic":
        raise DiscussionDemoError("Explicit synthetic classification is required")
    validate_fixture(payload)
    issue = session.get(Issue, "housing-rent")
    videos = {item.video_id: item for item in session.query(Video).filter(Video.video_id.in_(ALLOWED_VIDEO_IDS)).all()}
    if issue is None or set(videos) != ALLOWED_VIDEO_IDS:
        raise DiscussionDemoError("Load the reviewed Housing & Rent and three-video fixtures first")

    clear_fixture(session, classification=classification)
    users: dict[str, User] = {}
    for item in payload["users"]:
        user = User(
            email=f"{DEMO_EMAIL_PREFIX}{item['handle']}{DEMO_EMAIL_SUFFIX}",
            hashed_password="synthetic-demo-no-login",
            display_name=item["display_name"],
            digest_opt_in=0,
            alert_opt_in=0,
        )
        session.add(user)
        users[item["handle"]] = user
    session.flush()

    base_time = datetime(2026, 8, 18, 18, 0, tzinfo=timezone.utc)
    reply_total = reaction_total = 0
    for post_index, item in enumerate(payload["posts"]):
        post = DiscussionPost(
            author_id=users[item["author"]].id,
            author_label=users[item["author"]].display_name,
            body=item["body"].strip(),
            moderation_status="published",
            created_at=base_time - timedelta(minutes=post_index * 17),
        )
        session.add(post)
        session.flush()
        session.add(DiscussionAttachment(
            post_id=post.id,
            attachment_type="issue",
            issue_slug=issue.slug,
            label="Housing & Rent · demo context",
        ))
        if item.get("video_id"):
            session.add(DiscussionAttachment(
                post_id=post.id,
                attachment_type="video",
                video_id=item["video_id"],
                label=f"Reviewed video · {videos[item['video_id']].creator_label}",
            ))
        for reply_index, reply in enumerate(item.get("replies") or []):
            session.add(DiscussionReply(
                post_id=post.id,
                author_id=users[reply["author"]].id,
                body=reply["body"].strip(),
                moderation_status="published",
                created_at=post.created_at + timedelta(minutes=reply_index + 2),
            ))
            reply_total += 1
        post.reply_count = len(item.get("replies") or [])
        for reaction_index, handle in enumerate(item.get("likes") or []):
            session.add(DiscussionReaction(
                user_id=users[handle].id,
                target_type="post",
                target_id=post.id,
                reaction="like" if reaction_index % 2 == 0 else "insightful",
            ))
            reaction_total += 1
    session.commit()
    return {"users": len(users), "posts": len(payload["posts"]), "replies": reply_total, "reactions": reaction_total}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("load", "clear"))
    parser.add_argument("fixture", nargs="?", type=Path, default=Path("data/discussion_demo_synthetic.json"))
    args = parser.parse_args()
    assert_local_demo_environment()
    with SessionLocal() as session:
        result = clear_fixture(session, classification="synthetic") if args.action == "clear" else load_fixture(
            json.loads(args.fixture.read_text(encoding="utf-8")), session, classification="synthetic"
        )
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
