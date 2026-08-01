"""Add account-wide session invalidation version.

Revision ID: identity_lifecycle_001
Revises: phase6_solutions_001
"""

from alembic import op
import sqlalchemy as sa

revision = "identity_lifecycle_001"
down_revision = "phase6_solutions_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("session_version")
