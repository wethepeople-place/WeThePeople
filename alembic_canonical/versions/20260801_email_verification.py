"""Add first-class account email verification.

Revision ID: canonical_email_verify_001
Revises: canonical_identity_001
"""

from alembic import op
import sqlalchemy as sa

revision = "canonical_email_verify_001"
down_revision = "canonical_identity_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"])
    op.create_index("ix_email_verification_tokens_token_hash", "email_verification_tokens", ["token_hash"], unique=True)
    op.create_index("ix_email_verification_tokens_expires_at", "email_verification_tokens", ["expires_at"])
    op.create_index("ix_email_verification_tokens_consumed_at", "email_verification_tokens", ["consumed_at"])
    op.create_index("ix_email_verification_tokens_id", "email_verification_tokens", ["id"])


def downgrade() -> None:
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "email_verified_at")
