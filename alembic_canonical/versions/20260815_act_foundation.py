"""Add privacy-safe ACT foundation.

Revision ID: canonical_act_foundation_001
Revises: canonical_watch_interactions_001
"""

from alembic import op
import sqlalchemy as sa

revision = "canonical_act_foundation_001"
down_revision = "canonical_watch_interactions_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "official_office_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.String(), sa.ForeignKey("tracked_members.person_id", ondelete="CASCADE"), nullable=False),
        sa.Column("office_type", sa.String(20), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("contact_url", sa.String(500)),
        sa.Column("address", sa.String(500)),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("source_publisher", sa.String(200), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="verified"),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("person_id", "office_type", "phone", name="uq_official_contact_phone"),
        sa.CheckConstraint("office_type IN ('washington','district','state','contact_form')", name="ck_official_contact_type"),
        sa.CheckConstraint("verification_status IN ('verified','stale','withdrawn')", name="ck_official_contact_verification"),
    )
    for column in ("person_id", "office_type", "verification_status"):
        op.create_index(f"ix_official_office_contacts_{column}", "official_office_contacts", [column])

    op.create_table(
        "act_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("action_kind", sa.String(30), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=False),
        sa.Column("representative_id", sa.String(), sa.ForeignKey("tracked_members.person_id", ondelete="SET NULL")),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("private_note", sa.Text()),
        sa.Column("allow_aggregate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_act_receipt_user_key"),
        sa.CheckConstraint("action_kind IN ('call','message','follow','event','petition','circle','public_comment')", name="ck_act_receipt_kind"),
        sa.CheckConstraint("target_type IN ('video','discussion','issue','bill','vote','representative','solution','activity','circle')", name="ck_act_receipt_target"),
        sa.CheckConstraint("status IN ('prepared','opened','user_confirmed_submitted','response_received','attended','completed','cancelled')", name="ck_act_receipt_status"),
        sa.CheckConstraint("allow_aggregate IN (0,1)", name="ck_act_receipt_aggregate"),
    )
    for column in ("user_id", "action_kind", "target_type", "target_id", "representative_id", "status"):
        op.create_index(f"ix_act_receipts_{column}", "act_receipts", [column])

    op.create_table(
        "action_circles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organizer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("objective", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=False),
        sa.Column("geography", sa.String(120)),
        sa.Column("location_precision", sa.String(20), nullable=False, server_default="none"),
        sa.Column("membership_mode", sa.String(20), nullable=False, server_default="approval"),
        sa.Column("conduct_rules", sa.Text(), nullable=False),
        sa.Column("completion_condition", sa.String(500), nullable=False),
        sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_type IN ('video','discussion','issue','bill','vote','representative','solution','activity','circle')", name="ck_action_circle_target"),
        sa.CheckConstraint("membership_mode IN ('open','approval')", name="ck_action_circle_membership"),
        sa.CheckConstraint("moderation_status IN ('pending','published','hidden','archived','completed')", name="ck_action_circle_moderation"),
        sa.CheckConstraint("location_precision IN ('none','state','district','city')", name="ck_action_circle_location_precision"),
    )
    for column in ("organizer_id", "target_type", "target_id", "moderation_status"):
        op.create_index(f"ix_action_circles_{column}", "action_circles", [column])

    op.create_table(
        "action_circle_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("action_circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("circle_id", "user_id", name="uq_action_circle_member"),
        sa.CheckConstraint("role IN ('organizer','moderator','member')", name="ck_action_circle_role"),
        sa.CheckConstraint("status IN ('pending','active','declined','left','removed')", name="ck_action_circle_member_status"),
    )
    for column in ("circle_id", "user_id", "status"):
        op.create_index(f"ix_action_circle_memberships_{column}", "action_circle_memberships", [column])

    op.create_table(
        "civic_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("action_circles.id", ondelete="SET NULL")),
        sa.Column("organizer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("host_type", sa.String(20), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("timezone", sa.String(80), nullable=False),
        sa.Column("public_location", sa.String(500)),
        sa.Column("public_url", sa.String(500)),
        sa.Column("accessibility", sa.Text()),
        sa.Column("capacity", sa.Integer()),
        sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("host_type IN ('official','organization','community')", name="ck_civic_activity_host"),
        sa.CheckConstraint("format IN ('in_person','online','hybrid')", name="ck_civic_activity_format"),
        sa.CheckConstraint("moderation_status IN ('pending','published','cancelled','completed','hidden')", name="ck_civic_activity_moderation"),
    )
    for column in ("circle_id", "organizer_id", "starts_at", "moderation_status"):
        op.create_index(f"ix_civic_activities_{column}", "civic_activities", [column])

    op.create_table(
        "civic_activity_rsvps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("activity_id", sa.Integer(), sa.ForeignKey("civic_activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="going"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("activity_id", "user_id", name="uq_civic_activity_rsvp"),
        sa.CheckConstraint("status IN ('going','cancelled','attended')", name="ck_civic_activity_rsvp_status"),
    )
    for column in ("activity_id", "user_id"):
        op.create_index(f"ix_civic_activity_rsvps_{column}", "civic_activity_rsvps", [column])


def downgrade() -> None:
    for table in (
        "civic_activity_rsvps",
        "civic_activities",
        "action_circle_memberships",
        "action_circles",
        "act_receipts",
        "official_office_contacts",
    ):
        op.drop_table(table)
