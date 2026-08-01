"""add read-only Watch video schema

Revision ID: phase4_watch_001
Revises: housing_rent_slice_001
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa

revision = "phase4_watch_001"
down_revision = "housing_rent_slice_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("video_id", sa.String(length=100), primary_key=True),
        sa.Column("creator_label", sa.String(length=200), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("captions_url", sa.String(length=1000), nullable=True),
        sa.Column("media_url", sa.String(length=1000), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_videos_published_at", "videos", ["published_at"])
    op.create_index("ix_videos_sort_order", "videos", ["sort_order"])
    op.create_table(
        "video_issues",
        sa.Column("video_id", sa.String(length=100), primary_key=True),
        sa.Column("issue_slug", sa.String(length=100), primary_key=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.video_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_slug"], ["issues.slug"], ondelete="CASCADE"),
    )
    op.create_table(
        "video_bills",
        sa.Column("video_id", sa.String(length=100), primary_key=True),
        sa.Column("bill_id", sa.String(), primary_key=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.video_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.bill_id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("video_bills")
    op.drop_table("video_issues")
    op.drop_index("ix_videos_sort_order", table_name="videos")
    op.drop_index("ix_videos_published_at", table_name="videos")
    op.drop_table("videos")
