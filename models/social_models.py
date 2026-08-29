"""Normalized social records for the Discuss product layer.

These tables reuse the canonical user and civic-evidence identities. They do
not contain Firebase identifiers, private messages, ranking, or media storage.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.database import Base


class DiscussionPost(Base):
    __tablename__ = "discussion_posts"
    __table_args__ = (
        CheckConstraint(
            "moderation_status IN ('published','pending','hidden','removed')",
            name="ck_discussion_post_moderation_status",
        ),
        CheckConstraint("length(body) BETWEEN 1 AND 10000", name="ck_discussion_post_body_length"),
    )

    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    author_label = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    moderation_status = Column(String(20), nullable=False, server_default="published", index=True)
    reply_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    author = relationship("User")
    replies = relationship("DiscussionReply", back_populates="post", cascade="all, delete-orphan")
    attachments = relationship("DiscussionAttachment", back_populates="post", cascade="all, delete-orphan")
    video_link = relationship("DiscussionVideoLink", back_populates="post", cascade="all, delete-orphan", uselist=False)


class DiscussionVideoLink(Base):
    """A normalized external social-media link submitted with a community post."""

    __tablename__ = "discussion_video_links"
    __table_args__ = (
        UniqueConstraint("post_id", name="uq_discussion_video_link_post"),
        CheckConstraint(
            "provider IN ('youtube','tiktok','facebook','instagram')",
            name="ck_discussion_video_link_provider",
        ),
        CheckConstraint(
            "length(provider_video_id) BETWEEN 5 AND 100",
            name="ck_discussion_video_link_id_length",
        ),
    )

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(20), nullable=False)
    provider_video_id = Column(String(100), nullable=False, index=True)
    canonical_url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("DiscussionPost", back_populates="video_link")


class DiscussionReply(Base):
    __tablename__ = "discussion_replies"
    __table_args__ = (
        CheckConstraint(
            "moderation_status IN ('published','pending','hidden','removed')",
            name="ck_discussion_reply_moderation_status",
        ),
        CheckConstraint("length(body) BETWEEN 1 AND 10000", name="ck_discussion_reply_body_length"),
    )

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_reply_id = Column(Integer, ForeignKey("discussion_replies.id", ondelete="CASCADE"), nullable=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    moderation_status = Column(String(20), nullable=False, server_default="published", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    post = relationship("DiscussionPost", back_populates="replies")
    author = relationship("User")
    parent_reply = relationship("DiscussionReply", remote_side=[id], backref="child_replies")


class DiscussionAttachment(Base):
    __tablename__ = "discussion_attachments"
    __table_args__ = (
        UniqueConstraint("post_id", "video_id", name="uq_discussion_attachment_video"),
        UniqueConstraint("post_id", "issue_slug", name="uq_discussion_attachment_issue"),
        UniqueConstraint("post_id", "bill_id", name="uq_discussion_attachment_bill"),
        UniqueConstraint("post_id", "politician_id", name="uq_discussion_attachment_politician"),
        UniqueConstraint("post_id", "solution_id", name="uq_discussion_attachment_solution"),
        UniqueConstraint("post_id", "source_id", name="uq_discussion_attachment_source"),
        CheckConstraint(
            "attachment_type IN ('video','issue','bill','politician','solution','source')",
            name="ck_discussion_attachment_type",
        ),
        CheckConstraint(
            "(CASE WHEN video_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN issue_slug IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN bill_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN politician_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN solution_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN source_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_discussion_attachment_one_target",
        ),
    )

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_type = Column(String(20), nullable=False, index=True)
    video_id = Column(String(100), ForeignKey("videos.video_id", ondelete="RESTRICT"), nullable=True, index=True)
    issue_slug = Column(String(100), ForeignKey("issues.slug", ondelete="RESTRICT"), nullable=True, index=True)
    bill_id = Column(String, ForeignKey("bills.bill_id", ondelete="RESTRICT"), nullable=True, index=True)
    politician_id = Column(String(100), ForeignKey("tracked_members.person_id", ondelete="RESTRICT"), nullable=True, index=True)
    solution_id = Column(Integer, ForeignKey("proposals.id", ondelete="RESTRICT"), nullable=True, index=True)
    label = Column(String(500), nullable=True)
    source_id = Column(Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=True)

    post = relationship("DiscussionPost", back_populates="attachments")
    source = relationship("SourceDocument")


class DiscussionReaction(Base):
    __tablename__ = "discussion_reactions"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", "reaction", name="uq_discussion_reaction"),
        CheckConstraint("target_type IN ('post','reply')", name="ck_discussion_reaction_target"),
        CheckConstraint("reaction IN ('like','insightful','disagree')", name="ck_discussion_reaction_value"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = Column(String(10), nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    reaction = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DiscussionFollow(Base):
    __tablename__ = "discussion_follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "followed_id", name="uq_discussion_follow"),
        CheckConstraint("follower_id <> followed_id", name="ck_discussion_follow_not_self"),
    )

    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    followed_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DiscussionBookmark(Base):
    __tablename__ = "discussion_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_discussion_bookmark"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DiscussionEdit(Base):
    __tablename__ = "discussion_edits"
    __table_args__ = (CheckConstraint("target_type IN ('post','reply')", name="ck_discussion_edit_target"),)

    id = Column(Integer, primary_key=True)
    target_type = Column(String(10), nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    editor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    previous_body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DiscussionReport(Base):
    """Private moderation input; this table must never be exposed publicly."""

    __tablename__ = "discussion_reports"
    __table_args__ = (
        UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_discussion_report"),
        CheckConstraint("target_type IN ('post','reply','user')", name="ck_discussion_report_target"),
        CheckConstraint("status IN ('open','reviewing','resolved','dismissed')", name="ck_discussion_report_status"),
    )

    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_type = Column(String(10), nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    reason = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="open", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class DiscussionBlock(Base):
    """Private user safety preference; block relationships are never public."""

    __tablename__ = "discussion_blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_discussion_block"),
        CheckConstraint("blocker_id <> blocked_id", name="ck_discussion_block_not_self"),
    )

    id = Column(Integer, primary_key=True)
    blocker_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
