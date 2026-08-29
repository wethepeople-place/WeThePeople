"""Allow moderated discussion links from major social platforms.

Revision ID: canonical_discussion_social_links_002
Revises: canonical_forecast_review_002
"""

from alembic import op

revision = "canonical_discussion_social_links_002"
down_revision = "canonical_forecast_review_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("discussion_video_links") as batch:
        batch.drop_constraint("ck_discussion_video_link_provider", type_="check")
        batch.drop_constraint("ck_discussion_video_link_id_length", type_="check")
        batch.create_check_constraint(
            "ck_discussion_video_link_provider",
            "provider IN ('youtube','tiktok','facebook','instagram')",
        )
        batch.create_check_constraint(
            "ck_discussion_video_link_id_length",
            "length(provider_video_id) BETWEEN 5 AND 100",
        )


def downgrade() -> None:
    with op.batch_alter_table("discussion_video_links") as batch:
        batch.drop_constraint("ck_discussion_video_link_provider", type_="check")
        batch.drop_constraint("ck_discussion_video_link_id_length", type_="check")
        batch.create_check_constraint("ck_discussion_video_link_provider", "provider IN ('youtube')")
        batch.create_check_constraint("ck_discussion_video_link_id_length", "length(provider_video_id) = 11")
