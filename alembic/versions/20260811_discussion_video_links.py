"""Add normalized external video links for moderated discussion posts.

Revision ID: discussion_video_links_001
Revises: admin_suspension_001
"""

from alembic import op
import sqlalchemy as sa

revision = "discussion_video_links_001"
down_revision = "admin_suspension_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discussion_video_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_video_id", sa.String(length=100), nullable=False),
        sa.Column("canonical_url", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("provider IN ('youtube')", name="ck_discussion_video_link_provider"),
        sa.CheckConstraint("length(provider_video_id) = 11", name="ck_discussion_video_link_id_length"),
        sa.UniqueConstraint("post_id", name="uq_discussion_video_link_post"),
    )
    op.create_index("ix_discussion_video_links_post_id", "discussion_video_links", ["post_id"])
    op.create_index("ix_discussion_video_links_provider_video_id", "discussion_video_links", ["provider_video_id"])


def downgrade() -> None:
    op.drop_index("ix_discussion_video_links_provider_video_id", table_name="discussion_video_links")
    op.drop_index("ix_discussion_video_links_post_id", table_name="discussion_video_links")
    op.drop_table("discussion_video_links")
