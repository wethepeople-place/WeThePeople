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
