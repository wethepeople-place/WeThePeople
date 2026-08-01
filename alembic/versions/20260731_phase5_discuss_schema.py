"""add normalized Discuss social schema

Revision ID: phase5_discuss_001
Revises: phase4_watch_001
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa

revision = "phase5_discuss_001"
down_revision = "phase4_watch_001"
branch_labels = None
depends_on = None


def _timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "discussion_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("author_label", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("moderation_status", sa.String(20), server_default="published", nullable=False),
        sa.Column("reply_count", sa.Integer(), server_default="0", nullable=False),
        *_timestamps(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("moderation_status IN ('published','pending','hidden','removed')", name="ck_discussion_post_moderation_status"),
        sa.CheckConstraint("length(body) BETWEEN 1 AND 10000", name="ck_discussion_post_body_length"),
    )
    op.create_index("ix_discussion_posts_author_id", "discussion_posts", ["author_id"])
    op.create_index("ix_discussion_posts_moderation_status", "discussion_posts", ["moderation_status"])
    op.create_index("ix_discussion_posts_created_at", "discussion_posts", ["created_at"])

    op.create_table(
        "discussion_replies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("parent_reply_id", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("moderation_status", sa.String(20), server_default="published", nullable=False),
        *_timestamps(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["discussion_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_reply_id"], ["discussion_replies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("moderation_status IN ('published','pending','hidden','removed')", name="ck_discussion_reply_moderation_status"),
        sa.CheckConstraint("length(body) BETWEEN 1 AND 10000", name="ck_discussion_reply_body_length"),
    )
    for column in ("post_id", "parent_reply_id", "author_id", "moderation_status", "created_at"):
        op.create_index(f"ix_discussion_replies_{column}", "discussion_replies", [column])

    op.create_table(
        "discussion_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("attachment_type", sa.String(20), nullable=False),
        sa.Column("video_id", sa.String(100), nullable=True),
        sa.Column("issue_slug", sa.String(100), nullable=True),
        sa.Column("bill_id", sa.String(), nullable=True),
        sa.Column("politician_id", sa.String(100), nullable=True),
        sa.Column("solution_id", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(500), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["discussion_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.video_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["issue_slug"], ["issues.slug"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.bill_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["politician_id"], ["tracked_members.person_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["solution_id"], ["proposals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("post_id", "video_id", name="uq_discussion_attachment_video"),
        sa.UniqueConstraint("post_id", "issue_slug", name="uq_discussion_attachment_issue"),
        sa.UniqueConstraint("post_id", "bill_id", name="uq_discussion_attachment_bill"),
        sa.UniqueConstraint("post_id", "politician_id", name="uq_discussion_attachment_politician"),
        sa.UniqueConstraint("post_id", "solution_id", name="uq_discussion_attachment_solution"),
        sa.UniqueConstraint("post_id", "source_id", name="uq_discussion_attachment_source"),
        sa.CheckConstraint("attachment_type IN ('video','issue','bill','politician','solution','source')", name="ck_discussion_attachment_type"),
        sa.CheckConstraint(
            "(video_id IS NOT NULL) + (issue_slug IS NOT NULL) + (bill_id IS NOT NULL) + "
            "(politician_id IS NOT NULL) + (solution_id IS NOT NULL) + (source_id IS NOT NULL) = 1",
            name="ck_discussion_attachment_one_target",
        ),
    )
    for column in ("post_id", "attachment_type", "video_id", "issue_slug", "bill_id", "politician_id", "solution_id"):
        op.create_index(f"ix_discussion_attachments_{column}", "discussion_attachments", [column])

    op.create_table(
        "discussion_reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(10), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reaction", sa.String(20), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "target_type", "target_id", "reaction", name="uq_discussion_reaction"),
        sa.CheckConstraint("target_type IN ('post','reply')", name="ck_discussion_reaction_target"),
        sa.CheckConstraint("reaction IN ('like','insightful','disagree')", name="ck_discussion_reaction_value"),
    )
    for column in ("user_id", "target_type", "target_id"):
        op.create_index(f"ix_discussion_reactions_{column}", "discussion_reactions", [column])

    op.create_table(
        "discussion_follows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("followed_id", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["followed_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("follower_id", "followed_id", name="uq_discussion_follow"),
        sa.CheckConstraint("follower_id <> followed_id", name="ck_discussion_follow_not_self"),
    )
    op.create_index("ix_discussion_follows_follower_id", "discussion_follows", ["follower_id"])
    op.create_index("ix_discussion_follows_followed_id", "discussion_follows", ["followed_id"])

    op.create_table(
        "discussion_bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["discussion_posts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "post_id", name="uq_discussion_bookmark"),
    )
    op.create_index("ix_discussion_bookmarks_user_id", "discussion_bookmarks", ["user_id"])
    op.create_index("ix_discussion_bookmarks_post_id", "discussion_bookmarks", ["post_id"])

    op.create_table(
        "discussion_edits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_type", sa.String(10), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("editor_id", sa.Integer(), nullable=False),
        sa.Column("previous_body", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["editor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("target_type IN ('post','reply')", name="ck_discussion_edit_target"),
    )
    for column in ("target_type", "target_id", "editor_id"):
        op.create_index(f"ix_discussion_edits_{column}", "discussion_edits", [column])

    op.create_table(
        "discussion_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(10), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        *_timestamps(),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_discussion_report"),
        sa.CheckConstraint("target_type IN ('post','reply','user')", name="ck_discussion_report_target"),
        sa.CheckConstraint("status IN ('open','reviewing','resolved','dismissed')", name="ck_discussion_report_status"),
    )
    for column in ("reporter_id", "target_type", "target_id", "status"):
        op.create_index(f"ix_discussion_reports_{column}", "discussion_reports", [column])

    op.create_table(
        "discussion_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("blocker_id", sa.Integer(), nullable=False),
        sa.Column("blocked_id", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_discussion_block"),
        sa.CheckConstraint("blocker_id <> blocked_id", name="ck_discussion_block_not_self"),
    )
    op.create_index("ix_discussion_blocks_blocker_id", "discussion_blocks", ["blocker_id"])
    op.create_index("ix_discussion_blocks_blocked_id", "discussion_blocks", ["blocked_id"])


def downgrade() -> None:
    for table in (
        "discussion_blocks", "discussion_reports", "discussion_edits",
        "discussion_bookmarks", "discussion_follows", "discussion_reactions",
        "discussion_attachments", "discussion_replies", "discussion_posts",
    ):
        op.drop_table(table)
