"""Add non-monetary civic forecasting.

Revision ID: canonical_forecasting_001
Revises: canonical_act_foundation_001
"""

from alembic import op
import sqlalchemy as sa

revision = "canonical_forecasting_001"
down_revision = "canonical_act_foundation_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_markets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_type", sa.String(20), nullable=False),
        sa.Column("subject_id", sa.String(255), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("resolved_option", sa.String(120)),
        sa.Column("resolution_source_url", sa.String(500)),
        sa.Column("resolution_reason", sa.Text()),
        sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("market_type", "subject_id", name="uq_forecast_market_subject"),
        sa.CheckConstraint("market_type IN ('bill','election')", name="ck_forecast_market_type"),
        sa.CheckConstraint("status IN ('open','locked','resolved','void')", name="ck_forecast_market_status"),
    )
    for column in ("market_type", "subject_id", "status", "closes_at"):
        op.create_index(f"ix_forecast_markets_{column}", "forecast_markets", [column])
    op.create_table(
        "forecast_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("forecast_markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_key", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("market_id", "user_id", name="uq_forecast_prediction_user"),
    )
    op.create_index("ix_forecast_predictions_market_id", "forecast_predictions", ["market_id"])
    op.create_index("ix_forecast_predictions_user_id", "forecast_predictions", ["user_id"])


def downgrade() -> None:
    op.drop_table("forecast_predictions")
    op.drop_table("forecast_markets")
