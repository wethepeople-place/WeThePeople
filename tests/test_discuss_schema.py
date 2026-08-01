import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from models.auth_models import User
from models.database import Base
from models.social_models import (
    DiscussionAttachment,
    DiscussionBlock,
    DiscussionBookmark,
    DiscussionEdit,
    DiscussionFollow,
    DiscussionPost,
    DiscussionReaction,
    DiscussionReply,
    DiscussionReport,
)


EXPECTED_TABLES = {
    "discussion_posts",
    "discussion_replies",
    "discussion_attachments",
    "discussion_reactions",
    "discussion_follows",
    "discussion_bookmarks",
    "discussion_edits",
    "discussion_reports",
    "discussion_blocks",
}


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'discuss.db'}")
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)()


def _user(session, email):
    user = User(email=email, hashed_password="test-only", display_name=email.split("@")[0])
    session.add(user)
    session.flush()
    return user


def test_discuss_schema_reuses_canonical_identity_and_civic_foreign_keys(tmp_path):
    engine, _ = _session(tmp_path)
    inspector = inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())

    post_fks = {fk["referred_table"] for fk in inspector.get_foreign_keys("discussion_posts")}
    reply_fks = {fk["referred_table"] for fk in inspector.get_foreign_keys("discussion_replies")}
    attachment_fks = {
        fk["referred_table"] for fk in inspector.get_foreign_keys("discussion_attachments")
    }
    assert post_fks == {"users"}
    assert {"users", "discussion_posts", "discussion_replies"} <= reply_fks
    assert {
        "discussion_posts", "videos", "issues", "bills", "tracked_members",
        "proposals", "source_documents",
    } <= attachment_fks


def test_discuss_constraints_protect_identity_privacy_and_moderation_boundaries(tmp_path):
    _, session = _session(tmp_path)
    alice = _user(session, "alice@example.test")
    bob = _user(session, "bob@example.test")
    post = DiscussionPost(author_id=alice.id, author_label="Alice", body="A sourced opinion.")
    session.add(post)
    session.commit()

    reply = DiscussionReply(post_id=post.id, author_id=bob.id, body="A civil reply.")
    session.add(reply)
    session.commit()
    assert reply.moderation_status == "published"

    session.add(DiscussionBookmark(user_id=bob.id, post_id=post.id))
    session.add(DiscussionReaction(user_id=bob.id, target_type="post", target_id=post.id, reaction="insightful"))
    session.add(DiscussionFollow(follower_id=bob.id, followed_id=alice.id))
    session.add(DiscussionEdit(target_type="post", target_id=post.id, editor_id=alice.id, previous_body="Earlier wording"))
    session.add(DiscussionReport(reporter_id=bob.id, target_type="post", target_id=post.id, reason="other"))
    session.add(DiscussionBlock(blocker_id=bob.id, blocked_id=alice.id))
    session.commit()

    # Reports and blocks are private tables with no relationship attached to
    # the public post record, preventing accidental serializer traversal.
    assert not hasattr(post, "reports")
    assert not hasattr(post, "blocks")

    session.add(DiscussionFollow(follower_id=alice.id, followed_id=alice.id))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(DiscussionPost(author_label="Invalid", body="x", moderation_status="unreviewed"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(DiscussionAttachment(post_id=post.id, attachment_type="issue", label="Missing target"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_discuss_uniqueness_prevents_duplicate_social_edges(tmp_path):
    _, session = _session(tmp_path)
    alice = _user(session, "alice@example.test")
    bob = _user(session, "bob@example.test")
    session.commit()
    session.add(DiscussionFollow(follower_id=alice.id, followed_id=bob.id))
    session.commit()
    session.add(DiscussionFollow(follower_id=alice.id, followed_id=bob.id))
    with pytest.raises(IntegrityError):
        session.commit()
