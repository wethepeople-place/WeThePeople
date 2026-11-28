"""make vote roll-call uniqueness session-aware

Revision ID: canonical_vote_session_004
Revises: canonical_external_forecasts_003
Create Date: 2026-11-28
"""

from alembic import op


revision = "canonical_vote_session_004"
down_revision = "canonical_external_forecasts_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("votes") as batch_op:
        batch_op.drop_constraint(
            "uq_votes_congress_chamber_roll",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_votes_congress_chamber_session_roll",
            ["congress", "chamber", "vote_session", "roll_number"],
        )


def downgrade() -> None:
    with op.batch_alter_table("votes") as batch_op:
        batch_op.drop_constraint(
            "uq_votes_congress_chamber_session_roll",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_votes_congress_chamber_roll",
            ["congress", "chamber", "roll_number"],
        )

