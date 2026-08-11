"""Add private Watch likes and saves.

Revision ID: canonical_watch_interactions_001
Revises: canonical_discussion_video_links_001
"""

from alembic import op
import sqlalchemy as sa

revision = "canonical_watch_interactions_001"
down_revision = "canonical_discussion_video_links_001"
branch_labels = None
depends_on = None


def _table(name: str, unique_name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_id", sa.String(length=100), sa.ForeignKey("videos.video_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "video_id", name=unique_name),
    )
    op.create_index(f"ix_{name}_user_id", name, ["user_id"])
    op.create_index(f"ix_{name}_video_id", name, ["video_id"])


def upgrade() -> None:
    _table("video_likes", "uq_video_like_user_video")
    _table("video_saves", "uq_video_save_user_video")


def downgrade() -> None:
    for name in ("video_saves", "video_likes"):
        op.drop_index(f"ix_{name}_video_id", table_name=name)
        op.drop_index(f"ix_{name}_user_id", table_name=name)
        op.drop_table(name)
