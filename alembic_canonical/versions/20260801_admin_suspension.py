"""Add explicit administrator suspension state.

Revision ID: canonical_admin_suspend_001
Revises: canonical_email_verify_001
"""

from alembic import op
import sqlalchemy as sa

revision = "canonical_admin_suspend_001"
down_revision = "canonical_email_verify_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("suspension_reason", sa.String(500), nullable=True))
    op.create_index("ix_users_suspended_at", "users", ["suspended_at"])


def downgrade() -> None:
    op.drop_index("ix_users_suspended_at", table_name="users")
    op.drop_column("users", "suspension_reason")
    op.drop_column("users", "suspended_at")
