"""Add two-person forecast resolution review and immutable receipts.

Revision ID: canonical_forecast_review_002
Revises: canonical_forecasting_001
"""
from alembic import op
import sqlalchemy as sa

revision = "canonical_forecast_review_002"
down_revision = "canonical_forecasting_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_resolution_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("forecast_markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposal_type", sa.String(20), nullable=False, server_default="resolution"),
        sa.Column("proposed_status", sa.String(20), nullable=False),
        sa.Column("proposed_option", sa.String(120)),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("proposed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("proposed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_reason", sa.Text()),
        sa.CheckConstraint("proposed_status IN ('resolved','void')", name="ck_forecast_resolution_proposed_status"),
        sa.CheckConstraint("proposal_type IN ('resolution','correction')", name="ck_forecast_resolution_proposal_type"),
        sa.CheckConstraint("review_status IN ('pending','approved','rejected')", name="ck_forecast_resolution_review_status"),
    )
    op.create_index("ix_forecast_resolution_proposals_market_id", "forecast_resolution_proposals", ["market_id"])
    op.create_index("ix_forecast_resolution_proposals_review_status", "forecast_resolution_proposals", ["review_status"])
    op.create_table(
        "forecast_resolution_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("forecast_markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposal_id", sa.Integer(), sa.ForeignKey("forecast_resolution_proposals.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolved_option", sa.String(120)),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("aggregate_snapshot_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("market_id", "sequence", name="uq_forecast_receipt_sequence"),
    )
    op.create_index("ix_forecast_resolution_receipts_market_id", "forecast_resolution_receipts", ["market_id"])
    op.create_table(
        "forecast_resolution_appeals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("forecast_markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reporter_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False), sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending','accepted','rejected')", name="ck_forecast_appeal_status"),
    )
    op.create_index("ix_forecast_resolution_appeals_market_id", "forecast_resolution_appeals", ["market_id"])
    op.create_index("ix_forecast_resolution_appeals_reporter_user_id", "forecast_resolution_appeals", ["reporter_user_id"])
    op.create_index("ix_forecast_resolution_appeals_status", "forecast_resolution_appeals", ["status"])
    op.create_table(
        "reviewed_civic_promises",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("person_id", sa.String(100), nullable=False),
        sa.Column("person_name", sa.String(300), nullable=False), sa.Column("office", sa.String(300), nullable=False),
        sa.Column("exact_quote", sa.Text(), nullable=False), sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("promise_date", sa.DateTime(timezone=True), nullable=False), sa.Column("jurisdiction", sa.String(200), nullable=False),
        sa.Column("government_level", sa.String(30), nullable=False), sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measurable_criteria", sa.Text(), nullable=False), sa.Column("evidence_plan", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="draft"), sa.Column("template_version", sa.String(30), nullable=False),
        sa.Column("submitted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("government_level IN ('federal','state','local','tribal','territorial')", name="ck_reviewed_promise_government_level"),
        sa.CheckConstraint("review_status IN ('draft','pending','approved','rejected','retired')", name="ck_reviewed_promise_status"),
    )
    op.create_index("ix_reviewed_civic_promises_person_id", "reviewed_civic_promises", ["person_id"])
    op.create_index("ix_reviewed_civic_promises_review_status", "reviewed_civic_promises", ["review_status"])


def downgrade() -> None:
    op.drop_table("reviewed_civic_promises")
    op.drop_table("forecast_resolution_appeals")
    op.drop_table("forecast_resolution_receipts")
    op.drop_table("forecast_resolution_proposals")
