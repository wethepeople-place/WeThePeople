"""Non-monetary civic forecasting records.

Forecasts have no stake, price, payout, transferable balance, or prize. A user
may hold one current prediction per market and may revise it while the market
is open.
"""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.database import Base


class ForecastMarket(Base):
    __tablename__ = "forecast_markets"

    id = Column(Integer, primary_key=True)
    market_type = Column(String(20), nullable=False, index=True)
    subject_id = Column(String(255), nullable=False, index=True)
    question = Column(String(500), nullable=False)
    options_json = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, server_default="open", index=True)
    closes_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source_url = Column(String(500), nullable=False)
    resolved_option = Column(String(120))
    resolution_source_url = Column(String(500))
    resolution_reason = Column(Text)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("market_type", "subject_id", name="uq_forecast_market_subject"),
        CheckConstraint("market_type IN ('bill','election')", name="ck_forecast_market_type"),
        CheckConstraint("status IN ('open','locked','resolved','void')", name="ck_forecast_market_status"),
    )


class ForecastPrediction(Base):
    __tablename__ = "forecast_predictions"

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey("forecast_markets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    option_key = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    market = relationship("ForecastMarket")
    __table_args__ = (UniqueConstraint("market_id", "user_id", name="uq_forecast_prediction_user"),)


class ExternalForecastMarket(Base):
    """Read-only market signal imported from a third-party provider."""
    __tablename__ = "external_forecast_markets"

    id = Column(Integer, primary_key=True)
    provider = Column(String(30), nullable=False, index=True)
    provider_market_id = Column(String(255), nullable=False)
    provider_event_id = Column(String(255), index=True)
    slug = Column(String(500))
    question = Column(String(1000), nullable=False)
    description = Column(Text)
    outcomes_json = Column(JSON, nullable=False)
    implied_probabilities_json = Column(JSON, nullable=False)
    volume = Column(String(60))
    liquidity = Column(String(60))
    closes_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source_url = Column(String(1000), nullable=False)
    category = Column(String(100))
    quality_status = Column(String(30), nullable=False, server_default="published", index=True)
    quality_score = Column(Integer, nullable=False, server_default="0")
    quality_reasons_json = Column(JSON, nullable=False)
    matched_market_id = Column(Integer, ForeignKey("forecast_markets.id", ondelete="SET NULL"), index=True)
    last_observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("provider", "provider_market_id", name="uq_external_forecast_provider_market"),
        CheckConstraint("quality_status IN ('published','quarantined','closed')", name="ck_external_forecast_quality_status"),
    )


class ExternalForecastAudit(Base):
    __tablename__ = "external_forecast_audits"

    id = Column(Integer, primary_key=True)
    external_market_id = Column(Integer, ForeignKey("external_forecast_markets.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(40), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    reasons_json = Column(JSON, nullable=False)
    observed_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ForecastResolutionProposal(Base):
    """Append-only proposal requiring review by a different administrator."""
    __tablename__ = "forecast_resolution_proposals"

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey("forecast_markets.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_type = Column(String(20), nullable=False, server_default="resolution")
    proposed_status = Column(String(20), nullable=False)
    proposed_option = Column(String(120))
    source_url = Column(String(500), nullable=False)
    reason = Column(Text, nullable=False)
    review_status = Column(String(20), nullable=False, server_default="pending", index=True)
    proposed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    proposed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    review_reason = Column(Text)

    __table_args__ = (
        CheckConstraint("proposal_type IN ('resolution','correction')", name="ck_forecast_resolution_proposal_type"),
        CheckConstraint("proposed_status IN ('resolved','void')", name="ck_forecast_resolution_proposed_status"),
        CheckConstraint("review_status IN ('pending','approved','rejected')", name="ck_forecast_resolution_review_status"),
    )


class ForecastResolutionReceipt(Base):
    """Immutable public-safe record of an approved resolution decision."""
    __tablename__ = "forecast_resolution_receipts"

    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey("forecast_markets.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id = Column(Integer, ForeignKey("forecast_resolution_proposals.id", ondelete="RESTRICT"), nullable=False, unique=True)
    sequence = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    resolved_option = Column(String(120))
    source_url = Column(String(500), nullable=False)
    reason = Column(Text, nullable=False)
    aggregate_snapshot_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("market_id", "sequence", name="uq_forecast_receipt_sequence"),)


class ForecastResolutionAppeal(Base):
    """Private, source-backed challenge; never exposed before review."""
    __tablename__ = "forecast_resolution_appeals"
    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey("forecast_markets.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url = Column(String(500), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, server_default="pending", index=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    decision_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("status IN ('pending','accepted','rejected')", name="ck_forecast_appeal_status"),)


class ReviewedCivicPromise(Base):
    """A forecast-eligible promise, separate from community promise posts."""
    __tablename__ = "reviewed_civic_promises"
    id = Column(Integer, primary_key=True)
    person_id = Column(String(100), nullable=False, index=True)
    person_name = Column(String(300), nullable=False)
    office = Column(String(300), nullable=False)
    exact_quote = Column(Text, nullable=False)
    source_url = Column(String(500), nullable=False)
    promise_date = Column(DateTime(timezone=True), nullable=False)
    jurisdiction = Column(String(200), nullable=False)
    government_level = Column(String(30), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    measurable_criteria = Column(Text, nullable=False)
    evidence_plan = Column(Text, nullable=False)
    review_status = Column(String(20), nullable=False, server_default="draft", index=True)
    template_version = Column(String(30), nullable=False)
    submitted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("government_level IN ('federal','state','local','tribal','territorial')", name="ck_reviewed_promise_government_level"),
        CheckConstraint("review_status IN ('draft','pending','approved','rejected','retired')", name="ck_reviewed_promise_status"),
    )
