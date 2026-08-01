"""add relational citizen solution revisions and votes

Revision ID: phase6_solutions_001
Revises: phase5_discuss_001
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa

revision = "phase6_solutions_001"
down_revision = "phase5_discuss_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("proposals") as batch:
        batch.add_column(sa.Column("issue_slug", sa.String(100), nullable=True))
        batch.add_column(sa.Column("summary", sa.String(1000), nullable=True))
        batch.add_column(sa.Column("moderation_reason", sa.String(1000), nullable=True))
        batch.add_column(sa.Column("duplicate_of_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("latest_revision_number", sa.Integer(), server_default="1", nullable=False))
        batch.create_foreign_key("fk_proposals_issue_slug", "issues", ["issue_slug"], ["slug"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_proposals_duplicate_of", "proposals", ["duplicate_of_id"], ["id"], ondelete="RESTRICT")
        batch.create_index("ix_proposals_issue_slug", ["issue_slug"])

    op.create_table(
        "solution_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("solution_id", sa.Integer(), nullable=False),
        sa.Column("editor_user_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("change_note", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["solution_id"], ["proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["editor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("solution_id", "revision_number", name="uq_solution_revision_number"),
    )
    op.create_index("ix_solution_revisions_solution_id", "solution_revisions", ["solution_id"])
    op.create_index("ix_solution_revisions_editor_user_id", "solution_revisions", ["editor_user_id"])

    op.create_table(
        "solution_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("solution_id", sa.Integer(), nullable=False),
        sa.Column("voter_user_id", sa.Integer(), nullable=False),
        sa.Column("choice", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["solution_id"], ["proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("solution_id", "voter_user_id", name="uq_solution_vote_voter"),
        sa.CheckConstraint("choice IN ('support','oppose')", name="ck_solution_vote_choice"),
    )
    op.create_index("ix_solution_votes_solution_id", "solution_votes", ["solution_id"])
    op.create_index("ix_solution_votes_voter_user_id", "solution_votes", ["voter_user_id"])


def downgrade() -> None:
    op.drop_table("solution_votes")
    op.drop_table("solution_revisions")
    with op.batch_alter_table("proposals") as batch:
        batch.drop_index("ix_proposals_issue_slug")
        batch.drop_constraint("fk_proposals_duplicate_of", type_="foreignkey")
        batch.drop_constraint("fk_proposals_issue_slug", type_="foreignkey")
        for column in ("latest_revision_number", "duplicate_of_id", "moderation_reason", "summary", "issue_slug"):
            batch.drop_column(column)
