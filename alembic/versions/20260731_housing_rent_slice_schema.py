"""add issue-centered evidence schema

Revision ID: housing_rent_slice_001
Revises: anomaly_dedupe_idx_001
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "housing_rent_slice_001"
down_revision = "anomaly_dedupe_idx_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "issues",
        sa.Column("slug", sa.String(length=100), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "evidence_series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_slug", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("unit", sa.String(length=100), nullable=False),
        sa.Column("geography_type", sa.String(length=50), server_default="national", nullable=False),
        sa.Column("geography_id", sa.String(length=100), server_default="US", nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["issue_slug"], ["issues.slug"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("issue_slug", "key", "geography_type", "geography_id", name="uq_evidence_series_issue_key_geography"),
    )
    op.create_index("ix_evidence_series_issue_slug", "evidence_series", ["issue_slug"])
    op.create_index("ix_evidence_series_key", "evidence_series", ["key"])
    op.create_table(
        "evidence_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_record_id", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["evidence_series.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("series_id", "observation_date", name="uq_evidence_observation_series_date"),
    )
    op.create_index("ix_evidence_observations_series_id", "evidence_observations", ["series_id"])
    op.create_index("ix_evidence_observations_observation_date", "evidence_observations", ["observation_date"])
    op.create_table(
        "issue_bills",
        sa.Column("issue_slug", sa.String(length=100), primary_key=True),
        sa.Column("bill_id", sa.String(), primary_key=True),
        sa.Column("phase", sa.String(length=20), nullable=False),
        sa.Column("relevance_note", sa.Text(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["issue_slug"], ["issues.slug"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.bill_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "bill_committee_referrals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bill_id", sa.String(), nullable=False),
        sa.Column("committee_thomas_id", sa.String(), nullable=False),
        sa.Column("bill_action_id", sa.Integer(), nullable=True),
        sa.Column("referred_at", sa.Date(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.bill_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["committee_thomas_id"], ["committees.thomas_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["bill_action_id"], ["bill_actions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("bill_id", "committee_thomas_id", "referred_at", name="uq_bill_committee_referral"),
    )
    op.create_index("ix_bill_committee_referrals_bill_id", "bill_committee_referrals", ["bill_id"])
    op.create_index("ix_bill_committee_referrals_committee_thomas_id", "bill_committee_referrals", ["committee_thomas_id"])
    op.create_index("ix_bill_committee_referrals_bill_action_id", "bill_committee_referrals", ["bill_action_id"])
    op.create_index("ix_bill_committee_referrals_referred_at", "bill_committee_referrals", ["referred_at"])


def downgrade() -> None:
    op.drop_table("bill_committee_referrals")
    op.drop_table("issue_bills")
    op.drop_table("evidence_observations")
    op.drop_table("evidence_series")
    op.drop_table("issues")
