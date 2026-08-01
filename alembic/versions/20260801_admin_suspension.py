"""Add explicit administrator suspension state.

Revision ID: admin_suspension_001
Revises: email_verification_001
"""

from alembic import op
import sqlalchemy as sa

revision = "admin_suspension_001"
down_revision = "email_verification_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("suspension_reason", sa.String(500), nullable=True))
        batch.create_index("ix_users_suspended_at", ["suspended_at"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_suspended_at")
        batch.drop_column("suspension_reason")
        batch.drop_column("suspended_at")
