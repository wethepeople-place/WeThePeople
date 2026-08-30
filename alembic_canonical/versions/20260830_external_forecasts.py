"""Add automated external forecast signals and audit history.

Revision ID: canonical_external_forecasts_003
Revises: canonical_discussion_social_links_002
"""
from alembic import op
import sqlalchemy as sa

revision = "canonical_external_forecasts_003"
down_revision = "canonical_discussion_social_links_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_forecast_markets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_market_id", sa.String(255), nullable=False),
        sa.Column("provider_event_id", sa.String(255)), sa.Column("slug", sa.String(500)),
        sa.Column("question", sa.String(1000), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("outcomes_json", sa.JSON(), nullable=False),
        sa.Column("implied_probabilities_json", sa.JSON(), nullable=False),
        sa.Column("volume", sa.String(60)), sa.Column("liquidity", sa.String(60)),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False), sa.Column("category", sa.String(100)),
        sa.Column("quality_status", sa.String(30), nullable=False, server_default="published"),
        sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_reasons_json", sa.JSON(), nullable=False),
        sa.Column("matched_market_id", sa.Integer(), sa.ForeignKey("forecast_markets.id", ondelete="SET NULL")),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_market_id", name="uq_external_forecast_provider_market"),
        sa.CheckConstraint("quality_status IN ('published','quarantined','closed')", name="ck_external_forecast_quality_status"),
    )
    for column in ("provider", "provider_event_id", "closes_at", "quality_status", "matched_market_id", "last_observed_at"):
        op.create_index(f"ix_external_forecast_markets_{column}", "external_forecast_markets", [column])
    op.create_table(
        "external_forecast_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_market_id", sa.Integer(), sa.ForeignKey("external_forecast_markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False), sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("reasons_json", sa.JSON(), nullable=False), sa.Column("observed_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_external_forecast_audits_external_market_id", "external_forecast_audits", ["external_market_id"])
    op.create_index("ix_external_forecast_audits_action", "external_forecast_audits", ["action"])


def downgrade() -> None:
    op.drop_table("external_forecast_audits")
    op.drop_table("external_forecast_markets")
