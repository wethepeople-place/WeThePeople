"""Source-backed court cases linked to the canonical civic evidence graph."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.database import Base

CASE_STATUSES = ("filed", "pending", "stayed", "dismissed", "decided", "settled", "on_appeal", "closed")
EVENT_TYPES = ("filing", "hearing", "order", "decision", "dismissal", "settlement", "appeal", "other")
ASSERTION_KINDS = ("allegation", "procedural_event", "finding", "decision", "dismissal", "settlement", "appeal")
PARTY_ROLES = ("plaintiff", "defendant", "petitioner", "respondent", "appellant", "appellee", "intervenor", "other")


class CourtCase(Base):
    __tablename__ = "court_cases"
    __table_args__ = (
        UniqueConstraint("court_name", "docket_number", name="uq_court_case_docket"),
        CheckConstraint(f"procedural_status in {CASE_STATUSES}", name="ck_court_case_status"),
    )
    case_id = Column(String(150), primary_key=True)
    case_name = Column(String(500), nullable=False)
    court_name = Column(String(300), nullable=False)
    jurisdiction = Column(String(200), nullable=False)
    docket_number = Column(String(150), nullable=False)
    filed_date = Column(Date, nullable=False)
    procedural_status = Column(String(30), nullable=False, index=True)
    disposition = Column(Text, nullable=True)
    docket_url = Column(String(1000), nullable=False)
    source_id = Column(Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    source = relationship("SourceDocument")


class CourtCaseParty(Base):
    __tablename__ = "court_case_parties"
    __table_args__ = (
        UniqueConstraint("case_id", "name", "role", name="uq_court_case_party"),
        CheckConstraint(f"role in {PARTY_ROLES}", name="ck_court_case_party_role"),
    )
    id = Column(Integer, primary_key=True)
    case_id = Column(String(150), ForeignKey("court_cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    role = Column(String(30), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    case = relationship("CourtCase", backref="parties")


class CourtEvent(Base):
    __tablename__ = "court_events"
    __table_args__ = (
        CheckConstraint(f"event_type in {EVENT_TYPES}", name="ck_court_event_type"),
        CheckConstraint(f"assertion_kind in {ASSERTION_KINDS}", name="ck_court_event_assertion"),
    )
    id = Column(Integer, primary_key=True)
    case_id = Column(String(150), ForeignKey("court_cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    event_date = Column(Date, nullable=False, index=True)
    event_type = Column(String(30), nullable=False)
    assertion_kind = Column(String(30), nullable=False)
    summary = Column(Text, nullable=False)
    document_url = Column(String(1000), nullable=True)
    source_id = Column(Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    case = relationship("CourtCase", backref="events")
    source = relationship("SourceDocument")


class IssueCourtCase(Base):
    __tablename__ = "issue_court_cases"
    issue_slug = Column(String(100), ForeignKey("issues.slug", ondelete="CASCADE"), primary_key=True)
    case_id = Column(String(150), ForeignKey("court_cases.case_id", ondelete="CASCADE"), primary_key=True)
    relevance_note = Column(Text, nullable=False)
    source_id = Column(Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False)
    case = relationship("CourtCase", backref="issue_links")
    source = relationship("SourceDocument")


class BillCourtCase(Base):
    __tablename__ = "bill_court_cases"
    bill_id = Column(String, ForeignKey("bills.bill_id", ondelete="CASCADE"), primary_key=True)
    case_id = Column(String(150), ForeignKey("court_cases.case_id", ondelete="CASCADE"), primary_key=True)
    relationship_type = Column(String(50), nullable=False)
    source_id = Column(Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False)
    case = relationship("CourtCase", backref="bill_links")
    source = relationship("SourceDocument")
