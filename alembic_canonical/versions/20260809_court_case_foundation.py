"""Add source-backed court case foundation.

Revision ID: canonical_courts_001
Revises: canonical_admin_suspend_001
"""

from alembic import op
import sqlalchemy as sa

revision = "canonical_courts_001"
down_revision = "canonical_admin_suspend_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "court_cases",
        sa.Column("case_id", sa.String(150), primary_key=True),
        sa.Column("case_name", sa.String(500), nullable=False),
        sa.Column("court_name", sa.String(300), nullable=False),
        sa.Column("jurisdiction", sa.String(200), nullable=False),
        sa.Column("docket_number", sa.String(150), nullable=False),
        sa.Column("filed_date", sa.Date(), nullable=False),
        sa.Column("procedural_status", sa.String(30), nullable=False),
        sa.Column("disposition", sa.Text(), nullable=True),
        sa.Column("docket_url", sa.String(1000), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("court_name", "docket_number", name="uq_court_case_docket"),
        sa.CheckConstraint("procedural_status in ('filed','pending','stayed','dismissed','decided','settled','on_appeal','closed')", name="ck_court_case_status"),
    )
    op.create_index("ix_court_cases_procedural_status", "court_cases", ["procedural_status"])
    op.create_table(
        "court_case_parties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.String(150), sa.ForeignKey("court_cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("case_id", "name", "role", name="uq_court_case_party"),
        sa.CheckConstraint("role in ('plaintiff','defendant','petitioner','respondent','appellant','appellee','intervenor','other')", name="ck_court_case_party_role"),
    )
    op.create_index("ix_court_case_parties_case_id", "court_case_parties", ["case_id"])
    op.create_table(
        "court_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.String(150), sa.ForeignKey("court_cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("assertion_kind", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("document_url", sa.String(1000), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("event_type in ('filing','hearing','order','decision','dismissal','settlement','appeal','other')", name="ck_court_event_type"),
        sa.CheckConstraint("assertion_kind in ('allegation','procedural_event','finding','decision','dismissal','settlement','appeal')", name="ck_court_event_assertion"),
    )
    op.create_index("ix_court_events_case_id", "court_events", ["case_id"])
    op.create_index("ix_court_events_event_date", "court_events", ["event_date"])
    op.create_table(
        "issue_court_cases",
        sa.Column("issue_slug", sa.String(100), sa.ForeignKey("issues.slug", ondelete="CASCADE"), primary_key=True),
        sa.Column("case_id", sa.String(150), sa.ForeignKey("court_cases.case_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relevance_note", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_table(
        "bill_court_cases",
        sa.Column("bill_id", sa.String(), sa.ForeignKey("bills.bill_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("case_id", sa.String(150), sa.ForeignKey("court_cases.case_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bill_court_cases")
    op.drop_table("issue_court_cases")
    op.drop_index("ix_court_events_event_date", table_name="court_events")
    op.drop_index("ix_court_events_case_id", table_name="court_events")
    op.drop_table("court_events")
    op.drop_index("ix_court_case_parties_case_id", table_name="court_case_parties")
    op.drop_table("court_case_parties")
    op.drop_index("ix_court_cases_procedural_status", table_name="court_cases")
    op.drop_table("court_cases")
