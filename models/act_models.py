"""Canonical ACT models.

These tables connect civic records to deliberate user actions without storing
message bodies, call metadata, sensitive casework, or legal-intake details.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from models.database import Base


class OfficialOfficeContact(Base):
    __tablename__ = "official_office_contacts"
    __table_args__ = (
        UniqueConstraint("person_id", "office_type", "phone", name="uq_official_contact_phone"),
        CheckConstraint("office_type IN ('washington','district','state','contact_form')", name="ck_official_contact_type"),
        CheckConstraint("verification_status IN ('verified','stale','withdrawn')", name="ck_official_contact_verification"),
    )

    id = Column(Integer, primary_key=True)
    person_id = Column(String, ForeignKey("tracked_members.person_id", ondelete="CASCADE"), nullable=False, index=True)
    office_type = Column(String(20), nullable=False, index=True)
    label = Column(String(200), nullable=False)
    phone = Column(String(30), nullable=True)
    contact_url = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=False)
    source_publisher = Column(String(200), nullable=False)
    verification_status = Column(String(20), nullable=False, server_default="verified", index=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ActReceipt(Base):
    __tablename__ = "act_receipts"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_act_receipt_user_key"),
        CheckConstraint("action_kind IN ('call','message','follow','event','petition','circle','public_comment')", name="ck_act_receipt_kind"),
        CheckConstraint("target_type IN ('video','discussion','issue','bill','vote','representative','solution','activity','circle')", name="ck_act_receipt_target"),
        CheckConstraint("status IN ('prepared','opened','user_confirmed_submitted','response_received','attended','completed','cancelled')", name="ck_act_receipt_status"),
        CheckConstraint("allow_aggregate IN (0,1)", name="ck_act_receipt_aggregate"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key = Column(String(100), nullable=False)
    action_kind = Column(String(30), nullable=False, index=True)
    target_type = Column(String(30), nullable=False, index=True)
    target_id = Column(String(255), nullable=False, index=True)
    representative_id = Column(String, ForeignKey("tracked_members.person_id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(40), nullable=False, index=True)
    private_note = Column(Text, nullable=True)
    allow_aggregate = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ActionCircle(Base):
    __tablename__ = "action_circles"
    __table_args__ = (
        CheckConstraint("target_type IN ('video','discussion','issue','bill','vote','representative','solution','activity','circle')", name="ck_action_circle_target"),
        CheckConstraint("membership_mode IN ('open','approval')", name="ck_action_circle_membership"),
        CheckConstraint("moderation_status IN ('pending','published','hidden','archived','completed')", name="ck_action_circle_moderation"),
        CheckConstraint("location_precision IN ('none','state','district','city')", name="ck_action_circle_location_precision"),
    )

    id = Column(Integer, primary_key=True)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    objective = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    target_type = Column(String(30), nullable=False, index=True)
    target_id = Column(String(255), nullable=False, index=True)
    geography = Column(String(120), nullable=True)
    location_precision = Column(String(20), nullable=False, server_default="none")
    membership_mode = Column(String(20), nullable=False, server_default="approval")
    conduct_rules = Column(Text, nullable=False)
    completion_condition = Column(String(500), nullable=False)
    moderation_status = Column(String(20), nullable=False, server_default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ActionCircleMembership(Base):
    __tablename__ = "action_circle_memberships"
    __table_args__ = (
        UniqueConstraint("circle_id", "user_id", name="uq_action_circle_member"),
        CheckConstraint("role IN ('organizer','moderator','member')", name="ck_action_circle_role"),
        CheckConstraint("status IN ('pending','active','declined','left','removed')", name="ck_action_circle_member_status"),
    )

    id = Column(Integer, primary_key=True)
    circle_id = Column(Integer, ForeignKey("action_circles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False, server_default="member")
    status = Column(String(20), nullable=False, server_default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CivicActivity(Base):
    __tablename__ = "civic_activities"
    __table_args__ = (
        CheckConstraint("host_type IN ('official','organization','community')", name="ck_civic_activity_host"),
        CheckConstraint("format IN ('in_person','online','hybrid')", name="ck_civic_activity_format"),
        CheckConstraint("moderation_status IN ('pending','published','cancelled','completed','hidden')", name="ck_civic_activity_moderation"),
    )

    id = Column(Integer, primary_key=True)
    circle_id = Column(Integer, ForeignKey("action_circles.id", ondelete="SET NULL"), nullable=True, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    host_type = Column(String(20), nullable=False)
    format = Column(String(20), nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(String(80), nullable=False)
    public_location = Column(String(500), nullable=True)
    public_url = Column(String(500), nullable=True)
    accessibility = Column(Text, nullable=True)
    capacity = Column(Integer, nullable=True)
    moderation_status = Column(String(20), nullable=False, server_default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CivicActivityRsvp(Base):
    __tablename__ = "civic_activity_rsvps"
    __table_args__ = (
        UniqueConstraint("activity_id", "user_id", name="uq_civic_activity_rsvp"),
        CheckConstraint("status IN ('going','cancelled','attended')", name="ck_civic_activity_rsvp_status"),
    )

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("civic_activities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, server_default="going")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
