"""Issue-centered evidence links for bounded civic-data slices.

These tables extend the existing evidence foundation. Bills, bill actions,
people, committees, and source documents remain canonical in their existing
tables; this module only adds the relationships needed to assemble an issue.
"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.database import Base


class Issue(Base):
    __tablename__ = "issues"

    slug = Column(String(100), primary_key=True)
    title = Column(String(300), nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EvidenceSeries(Base):
    __tablename__ = "evidence_series"
    __table_args__ = (
        UniqueConstraint(
            "issue_slug",
            "key",
            "geography_type",
            "geography_id",
            name="uq_evidence_series_issue_key_geography",
        ),
    )

    id = Column(Integer, primary_key=True)
    issue_slug = Column(
        String(100), ForeignKey("issues.slug", ondelete="CASCADE"), nullable=False, index=True
    )
    key = Column(String(100), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    unit = Column(String(100), nullable=False)
    geography_type = Column(String(50), nullable=False, server_default="national")
    geography_id = Column(String(100), nullable=False, server_default="US")
    source_id = Column(
        Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    issue = relationship("Issue", backref="evidence_series")
    source = relationship("SourceDocument")


class EvidenceObservation(Base):
    __tablename__ = "evidence_observations"
    __table_args__ = (
        UniqueConstraint(
            "series_id", "observation_date", name="uq_evidence_observation_series_date"
        ),
    )

    id = Column(Integer, primary_key=True)
    series_id = Column(
        Integer, ForeignKey("evidence_series.id", ondelete="CASCADE"), nullable=False, index=True
    )
    observation_date = Column(Date, nullable=False, index=True)
    value = Column(Float, nullable=False)
    source_id = Column(
        Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False
    )
    source_record_id = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    series = relationship("EvidenceSeries", backref="observations")
    source = relationship("SourceDocument")


class IssueBill(Base):
    __tablename__ = "issue_bills"

    issue_slug = Column(
        String(100), ForeignKey("issues.slug", ondelete="CASCADE"), primary_key=True
    )
    bill_id = Column(
        String, ForeignKey("bills.bill_id", ondelete="CASCADE"), primary_key=True
    )
    phase = Column(String(20), nullable=False)
    relevance_note = Column(Text, nullable=True)
    source_id = Column(
        Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    issue = relationship("Issue", backref="bill_links")
    bill = relationship("Bill", backref="issue_links")
    source = relationship("SourceDocument")


class BillCommitteeReferral(Base):
    __tablename__ = "bill_committee_referrals"
    __table_args__ = (
        UniqueConstraint(
            "bill_id",
            "committee_thomas_id",
            "referred_at",
            name="uq_bill_committee_referral",
        ),
    )

    id = Column(Integer, primary_key=True)
    bill_id = Column(
        String, ForeignKey("bills.bill_id", ondelete="CASCADE"), nullable=False, index=True
    )
    committee_thomas_id = Column(
        String,
        ForeignKey("committees.thomas_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bill_action_id = Column(
        Integer, ForeignKey("bill_actions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    referred_at = Column(Date, nullable=False, index=True)
    source_id = Column(
        Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bill = relationship("Bill", backref="committee_referrals")
    committee = relationship("Committee", backref="bill_referrals")
    bill_action = relationship("BillAction")
    source = relationship("SourceDocument")


class Video(Base):
    """A curated, source-backed Watch item; social activity is intentionally absent."""

    __tablename__ = "videos"

    video_id = Column(String(100), primary_key=True)
    creator_label = Column(String(200), nullable=False)
    caption = Column(Text, nullable=False)
    transcript = Column(Text, nullable=True)
    captions_url = Column(String(1000), nullable=True)
    media_url = Column(String(1000), nullable=False)
    source_id = Column(Integer, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, server_default="0", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    source = relationship("SourceDocument")


class VideoIssue(Base):
    __tablename__ = "video_issues"

    video_id = Column(String(100), ForeignKey("videos.video_id", ondelete="CASCADE"), primary_key=True)
    issue_slug = Column(String(100), ForeignKey("issues.slug", ondelete="CASCADE"), primary_key=True)

    video = relationship("Video", backref="issue_links")
    issue = relationship("Issue")


class VideoBill(Base):
    __tablename__ = "video_bills"

    video_id = Column(String(100), ForeignKey("videos.video_id", ondelete="CASCADE"), primary_key=True)
    bill_id = Column(String, ForeignKey("bills.bill_id", ondelete="CASCADE"), primary_key=True)

    video = relationship("Video", backref="bill_links")
    bill = relationship("Bill")
