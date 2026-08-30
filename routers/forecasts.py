"""Civic forecasts: opinions, not gambling or financial products."""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.auth_models import User
from models.database import Bill, get_db
from models.forecast_models import (
    ExternalForecastMarket, ForecastMarket, ForecastPrediction, ForecastResolutionProposal, ForecastResolutionReceipt,
    ForecastResolutionAppeal,
    ReviewedCivicPromise,
)
from services.audit import log_from_request
from services.forecast_tokens import verify_election_contest
from services.jwt_auth import get_current_user, get_optional_user
from services.rbac import require_role

router = APIRouter(prefix="/forecasts", tags=["forecasts"])
MIN_PUBLIC_RESPONSES = 5
DEMO_EMAIL_PREFIX = "demo.discussion."
LEGISLATION_RESOLUTION_HOSTS = {"congress.gov", "www.congress.gov", "govinfo.gov", "www.govinfo.gov"}


def _protect_private_forecast_response(response: Response) -> None:
    """Prevent browsers or intermediaries from retaining a viewer's choice."""
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, Cookie"


def _reject_synthetic_user(user: User) -> None:
    if user.email.lower().startswith(DEMO_EMAIL_PREFIX):
        raise HTTPException(status_code=403, detail="Synthetic demo accounts cannot participate in Civic Forecasts")


def _approved_resolution_source(market: ForecastMarket, source_url: str) -> bool:
    host = (urlparse(source_url).hostname or "").lower()
    if market.market_type == "bill":
        return host in LEGISLATION_RESOLUTION_HOSTS
    if market.market_type == "election":
        original_host = (urlparse(market.source_url).hostname or "").lower()
        return host.endswith(".gov") or host == original_host
    return False


class PredictionWrite(BaseModel):
    option_key: str = Field(min_length=1, max_length=120)


class ElectionPredictionWrite(PredictionWrite):
    contest_token: str = Field(min_length=20, max_length=5000)


class ElectionMarketLookup(BaseModel):
    contest_token: str = Field(min_length=20, max_length=5000)


class ResolutionWrite(BaseModel):
    status: Literal["resolved", "void"]
    resolved_option: str | None = Field(default=None, max_length=120)
    source_url: str = Field(min_length=8, max_length=500, pattern=r"^https://")
    reason: str = Field(min_length=20, max_length=2000)


class ResolutionReview(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=20, max_length=2000)


class AppealWrite(BaseModel):
    source_url: str = Field(min_length=8, max_length=500, pattern=r"^https://")
    reason: str = Field(min_length=40, max_length=3000)


class AppealReview(BaseModel):
    decision: Literal["accepted", "rejected"]
    reason: str = Field(min_length=20, max_length=2000)


class ReviewedPromiseWrite(BaseModel):
    person_id: str = Field(min_length=1, max_length=100)
    person_name: str = Field(min_length=2, max_length=300)
    office: str = Field(min_length=2, max_length=300)
    exact_quote: str = Field(min_length=10, max_length=5000)
    source_url: str = Field(min_length=8, max_length=500, pattern=r"^https://")
    promise_date: datetime
    jurisdiction: str = Field(min_length=2, max_length=200)
    government_level: Literal["federal", "state", "local", "tribal", "territorial"]
    deadline: datetime
    measurable_criteria: str = Field(min_length=40, max_length=5000)
    evidence_plan: str = Field(min_length=40, max_length=5000)
    template_version: str = Field(min_length=1, max_length=30)


class ReviewedPromiseDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=20, max_length=2000)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def promise_forecasts_enabled() -> bool:
    """Fail closed; counsel and owner must explicitly enable production use."""
    return os.getenv("WTP_ENABLE_REVIEWED_PROMISE_FORECASTS", "false").lower() == "true"


def _market_payload(market: ForecastMarket, db: Session, user: User | None) -> dict:
    rows = db.query(ForecastPrediction.option_key).filter_by(market_id=market.id).all()
    counts = {str(option["key"]): 0 for option in market.options_json}
    for (choice,) in rows:
        if choice in counts:
            counts[choice] += 1
    total = sum(counts.values())
    visible = total >= MIN_PUBLIC_RESPONSES
    current = None
    if user:
        prediction = db.query(ForecastPrediction).filter_by(market_id=market.id, user_id=user.id).first()
        current = prediction.option_key if prediction else None
    return {
        "id": market.id,
        "market_type": market.market_type,
        "subject_id": market.subject_id,
        "question": market.question,
        "options": [{**option, "responses": counts[option["key"]] if visible else None,
                     "share": round(counts[option["key"]] * 100 / total) if visible and total else None}
                    for option in market.options_json],
        "status": "locked" if market.status == "open" and _utc(market.closes_at) <= datetime.now(timezone.utc) else market.status,
        "closes_at": market.closes_at.isoformat(),
        "source_url": market.source_url,
        "response_count": total if visible else None,
        "privacy_threshold": MIN_PUBLIC_RESPONSES,
        "current_user_choice": current,
        "resolved_option": market.resolved_option,
        "resolution_source_url": market.resolution_source_url,
        "resolution_reason": market.resolution_reason,
        "resolved_at": market.resolved_at.isoformat() if market.resolved_at else None,
        "rules": "One changeable forecast per signed-in user. No money, purchases, prizes, payouts, or transferable points.",
    }


def _save_prediction(market: ForecastMarket, choice: str, user: User, db: Session) -> None:
    _reject_synthetic_user(user)
    if market.status != "open" or _utc(market.closes_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="This forecast is closed")
    choices = {str(option["key"]) for option in market.options_json}
    if choice not in choices:
        raise HTTPException(status_code=422, detail="Choose one of the published forecast options")
    row = db.query(ForecastPrediction).filter_by(market_id=market.id, user_id=user.id).first()
    if row is None:
        row = ForecastPrediction(market_id=market.id, user_id=user.id, option_key=choice)
        db.add(row)
    else:
        row.option_key = choice
    db.commit()


def _bill_market(bill: Bill, db: Session) -> ForecastMarket:
    market = db.query(ForecastMarket).filter_by(market_type="bill", subject_id=bill.bill_id).first()
    if market:
        return market
    closes_at = datetime(bill.congress + 1908, 1, 3, tzinfo=timezone.utc)
    type_paths = {
        "hr": "house-bill", "s": "senate-bill", "hjres": "house-joint-resolution",
        "sjres": "senate-joint-resolution", "hconres": "house-concurrent-resolution",
        "sconres": "senate-concurrent-resolution", "hres": "house-resolution", "sres": "senate-resolution",
    }
    market = ForecastMarket(
        market_type="bill", subject_id=bill.bill_id,
        question=f"Will {bill.bill_type.upper()}. {bill.bill_number} become law before the end of the {bill.congress}th Congress?",
        options_json=[{"key": "yes", "label": "Yes"}, {"key": "no", "label": "No"}],
        closes_at=closes_at,
        source_url=f"https://www.congress.gov/bill/{bill.congress}th-congress/{type_paths.get(bill.bill_type, 'house-bill')}/{bill.bill_number}",
    )
    db.add(market)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        market = db.query(ForecastMarket).filter_by(market_type="bill", subject_id=bill.bill_id).one()
    db.refresh(market)
    return market


def _election_market_identity(contest_token: str) -> tuple[dict, str]:
    try:
        contest = verify_election_contest(contest_token)
    except JWTError as exc:
        raise HTTPException(status_code=422, detail="Election forecast reference expired; refresh your official ballot") from exc
    options = contest.get("options") or []
    canonical = json.dumps({"election_id": contest.get("election_id"), "office": contest.get("office"),
                            "district": contest.get("district"), "options": options}, sort_keys=True, separators=(",", ":"))
    return contest, f"{contest.get('election_id')}:{hashlib.sha256(canonical.encode()).hexdigest()[:24]}"


@router.get("")
def open_forecasts(response: Response, market_type: Literal["bill", "election"] | None = None,
                   limit: int = Query(default=50, ge=1, le=100),
                   user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    query = db.query(ForecastMarket).filter(
        ForecastMarket.status == "open",
        ForecastMarket.closes_at > datetime.now(timezone.utc),
    )
    if market_type:
        query = query.filter(ForecastMarket.market_type == market_type)
    markets = query.order_by(ForecastMarket.closes_at.asc(), ForecastMarket.id.asc()).limit(limit).all()
    return {"items": [_market_payload(market, db, user) for market in markets], "privacy_threshold": MIN_PUBLIC_RESPONSES}


@router.get("/external")
def external_forecasts(response: Response, provider: Literal["polymarket"] = "polymarket",
                       limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
                       db: Session = Depends(get_db)):
    """Published read-only signals that passed the automated quality bot."""
    _protect_private_forecast_response(response)
    now = datetime.now(timezone.utc)
    query = db.query(ExternalForecastMarket).filter(
        ExternalForecastMarket.provider == provider,
        ExternalForecastMarket.quality_status == "published",
        ExternalForecastMarket.closes_at > now,
    )
    total = query.count()
    rows = query.order_by(ExternalForecastMarket.quality_score.desc(), ExternalForecastMarket.last_observed_at.desc()).offset(offset).limit(limit).all()
    return {"provider": provider, "total": total, "limit": limit, "offset": offset, "items": [{
        "id": row.id, "provider_market_id": row.provider_market_id, "question": row.question,
        "outcomes": [{"label": label, "probability": round(float(row.implied_probabilities_json[index]) * 100, 1)}
                     for index, label in enumerate(row.outcomes_json)],
        "volume": float(row.volume or 0), "liquidity": float(row.liquidity or 0),
        "closes_at": row.closes_at.isoformat(), "source_url": row.source_url,
        "observed_at": row.last_observed_at.isoformat(), "quality_score": row.quality_score,
        "matched_market_id": row.matched_market_id,
        "label": "Polymarket market-implied probability",
    } for row in rows]}


@router.get("/bills/{bill_id}")
def bill_forecast(bill_id: str, response: Response, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    market = db.query(ForecastMarket).filter_by(market_type="bill", subject_id=bill_id).first()
    if market is None:
        raise HTTPException(status_code=404, detail="No forecast has been opened for this bill")
    return _market_payload(market, db, user)


@router.put("/bills/{bill_id}")
def predict_bill(bill_id: str, body: PredictionWrite, response: Response,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    _reject_synthetic_user(user)
    bill = db.get(Bill, bill_id)
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found")
    market = _bill_market(bill, db)
    _save_prediction(market, body.option_key, user, db)
    return _market_payload(market, db, user)


@router.put("/elections")
def predict_election(body: ElectionPredictionWrite, response: Response,
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    _reject_synthetic_user(user)
    contest, subject_id = _election_market_identity(body.contest_token)
    options = contest.get("options") or []
    market = db.query(ForecastMarket).filter_by(market_type="election", subject_id=subject_id).first()
    if market is None:
        market = ForecastMarket(
            market_type="election", subject_id=subject_id,
            question=f"Who will win {contest.get('office')}" + (f" · {contest.get('district')}?" if contest.get("district") else "?"),
            options_json=options, closes_at=datetime.fromisoformat(str(contest["closes_at"]).replace("Z", "+00:00")),
            source_url=str(contest["source_url"]),
        )
        db.add(market)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            market = db.query(ForecastMarket).filter_by(market_type="election", subject_id=subject_id).one()
        db.refresh(market)
    _save_prediction(market, body.option_key, user, db)
    return _market_payload(market, db, user)


@router.post("/elections/market")
def election_forecast(body: ElectionMarketLookup, response: Response,
                      user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    _, subject_id = _election_market_identity(body.contest_token)
    market = db.query(ForecastMarket).filter_by(market_type="election", subject_id=subject_id).first()
    if market is None:
        raise HTTPException(status_code=404, detail="No forecast has been opened for this contest")
    return _market_payload(market, db, user)


@router.post("/admin/{market_id}/resolution-proposals", status_code=201)
@router.patch("/admin/{market_id}", status_code=201)
def propose_resolution(market_id: int, body: ResolutionWrite, request: Request,
                   response: Response, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    market = db.get(ForecastMarket, market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Forecast not found")
    if market.status in {"resolved", "void"}:
        raise HTTPException(status_code=409, detail="A final forecast resolution cannot be replaced")
    options = {str(option["key"]) for option in market.options_json}
    if body.status == "resolved" and body.resolved_option not in options:
        raise HTTPException(status_code=422, detail="Resolution must match a published option")
    if not _approved_resolution_source(market, body.source_url):
        raise HTTPException(status_code=422, detail="Resolution source must be an approved authoritative publisher")
    pending = db.query(ForecastResolutionProposal).filter_by(market_id=market.id, review_status="pending").first()
    if pending:
        raise HTTPException(status_code=409, detail="This forecast already has a pending resolution proposal")
    proposal = ForecastResolutionProposal(
        market_id=market.id, proposed_status=body.status,
        proposed_option=body.resolved_option if body.status == "resolved" else None,
        source_url=body.source_url, reason=body.reason, proposed_by_user_id=admin.id,
    )
    db.add(proposal)
    log_from_request(db, request, action="forecast_resolution_proposed", user_id=admin.id,
                     resource="forecast_market", resource_id=str(market.id),
                     details={"status": body.status, "option": body.resolved_option, "source_url": body.source_url, "reason": body.reason})
    db.commit()
    db.refresh(proposal)
    return {"id": proposal.id, "market_id": market.id, "review_status": "pending",
            "message": "A different administrator must approve this proposal before it takes effect."}


@router.post("/admin/{market_id}/correction-proposals", status_code=201)
def propose_correction(market_id: int, body: ResolutionWrite, request: Request, response: Response,
                       admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    market = db.get(ForecastMarket, market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Forecast not found")
    if market.status not in {"resolved", "void"}:
        raise HTTPException(status_code=409, detail="Only a finalized forecast can receive a correction")
    options = {str(option["key"]) for option in market.options_json}
    if body.status == "resolved" and body.resolved_option not in options:
        raise HTTPException(status_code=422, detail="Correction must match a published option")
    if not _approved_resolution_source(market, body.source_url):
        raise HTTPException(status_code=422, detail="Correction source must be an approved authoritative publisher")
    if db.query(ForecastResolutionProposal).filter_by(market_id=market.id, review_status="pending").first():
        raise HTTPException(status_code=409, detail="This forecast already has a pending proposal")
    proposal = ForecastResolutionProposal(
        market_id=market.id, proposal_type="correction", proposed_status=body.status,
        proposed_option=body.resolved_option if body.status == "resolved" else None,
        source_url=body.source_url, reason=body.reason, proposed_by_user_id=admin.id,
    )
    db.add(proposal)
    log_from_request(db, request, action="forecast_correction_proposed", user_id=admin.id,
                     resource="forecast_market", resource_id=str(market.id),
                     details={"status": body.status, "option": body.resolved_option, "source_url": body.source_url})
    db.commit(); db.refresh(proposal)
    return {"id": proposal.id, "market_id": market.id, "proposal_type": "correction", "review_status": "pending"}


@router.post("/admin/resolution-proposals/{proposal_id}/review")
def review_resolution(proposal_id: int, body: ResolutionReview, request: Request, response: Response,
                      admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    proposal = db.get(ForecastResolutionProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Resolution proposal not found")
    if proposal.review_status != "pending":
        raise HTTPException(status_code=409, detail="This proposal has already been reviewed")
    if proposal.proposed_by_user_id == admin.id:
        raise HTTPException(status_code=403, detail="A different administrator must review this proposal")
    market = db.get(ForecastMarket, proposal.market_id)
    if market is None:
        raise HTTPException(status_code=409, detail="Forecast no longer exists")
    if proposal.proposal_type == "resolution" and market.status in {"resolved", "void"}:
        raise HTTPException(status_code=409, detail="Forecast is no longer eligible for initial resolution")
    if proposal.proposal_type == "correction" and market.status not in {"resolved", "void"}:
        raise HTTPException(status_code=409, detail="Forecast is not eligible for correction")
    proposal.review_status = body.decision
    proposal.reviewed_by_user_id = admin.id
    proposal.reviewed_at = datetime.now(timezone.utc)
    proposal.review_reason = body.reason
    if body.decision == "approved":
        rows = db.query(ForecastPrediction.option_key).filter_by(market_id=market.id).all()
        counts = {str(o["key"]): 0 for o in market.options_json}
        for (choice,) in rows:
            if choice in counts:
                counts[choice] += 1
        total = sum(counts.values())
        sequence = db.query(ForecastResolutionReceipt).filter_by(market_id=market.id).count() + 1
        receipt = ForecastResolutionReceipt(
            market_id=market.id, proposal_id=proposal.id, sequence=sequence,
            status=proposal.proposed_status, resolved_option=proposal.proposed_option,
            source_url=proposal.source_url, reason=proposal.reason,
            aggregate_snapshot_json={"total": total, "counts": counts} if total >= MIN_PUBLIC_RESPONSES else None,
        )
        db.add(receipt)
        market.status = proposal.proposed_status
        market.resolved_option = proposal.proposed_option if proposal.proposed_status == "resolved" else None
        market.resolution_source_url = proposal.source_url
        market.resolution_reason = proposal.reason
        market.resolved_by_user_id = admin.id
        market.resolved_at = proposal.reviewed_at
    log_from_request(db, request, action=f"forecast_resolution_{body.decision}", user_id=admin.id,
                     resource="forecast_resolution_proposal", resource_id=str(proposal.id),
                     details={"review_reason": body.reason})
    db.commit()
    return {"id": proposal.id, "review_status": proposal.review_status,
            "market": _market_payload(market, db, admin)}


@router.post("/{market_id}/appeals", status_code=201)
def submit_resolution_appeal(market_id: int, body: AppealWrite, request: Request, response: Response,
                             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    _reject_synthetic_user(user)
    market = db.get(ForecastMarket, market_id)
    if market is None or market.status not in {"resolved", "void"}:
        raise HTTPException(status_code=409, detail="Only a finalized forecast can be appealed")
    appeal = ForecastResolutionAppeal(
        market_id=market.id, reporter_user_id=user.id,
        source_url=body.source_url, reason=body.reason,
    )
    db.add(appeal)
    log_from_request(db, request, action="forecast_resolution_appealed", user_id=user.id,
                     resource="forecast_market", resource_id=str(market.id), details={"appeal_id": None})
    db.commit(); db.refresh(appeal)
    return {"id": appeal.id, "status": "pending", "visibility": "private_until_reviewed"}


@router.post("/admin/appeals/{appeal_id}/review")
def review_appeal(appeal_id: int, body: AppealReview, request: Request, response: Response,
                  admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    appeal = db.get(ForecastResolutionAppeal, appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if appeal.status != "pending":
        raise HTTPException(status_code=409, detail="Appeal has already been reviewed")
    appeal.status = body.decision; appeal.decision_reason = body.reason
    appeal.reviewed_by_user_id = admin.id; appeal.reviewed_at = datetime.now(timezone.utc)
    log_from_request(db, request, action=f"forecast_appeal_{body.decision}", user_id=admin.id,
                     resource="forecast_resolution_appeal", resource_id=str(appeal.id), details={"reason": body.reason})
    db.commit()
    return {"id": appeal.id, "status": appeal.status,
            "next_step": "Submit a two-person correction proposal" if appeal.status == "accepted" else None}


@router.get("/{market_id}/receipts")
def public_resolution_receipts(market_id: int, response: Response, db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    market = db.get(ForecastMarket, market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Forecast not found")
    receipts = db.query(ForecastResolutionReceipt).filter_by(market_id=market_id).order_by(ForecastResolutionReceipt.sequence).all()
    return {"market_id": market_id, "question": market.question, "options": market.options_json,
            "closes_at": market.closes_at.isoformat(), "receipts": [{
                "sequence": r.sequence, "status": r.status, "resolved_option": r.resolved_option,
                "source_url": r.source_url, "reason": r.reason, "aggregate": r.aggregate_snapshot_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "supersedes_sequence": r.sequence - 1 if r.sequence > 1 else None,
            } for r in receipts]}


@router.post("/admin/reviewed-promises", status_code=201)
def submit_reviewed_promise(body: ReviewedPromiseWrite, request: Request, response: Response,
                            admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    if _utc(body.deadline) <= _utc(body.promise_date):
        raise HTTPException(status_code=422, detail="Promise deadline must be after the documented promise date")
    item = ReviewedCivicPromise(
        **body.model_dump(), review_status="pending", submitted_by_user_id=admin.id,
    )
    db.add(item)
    log_from_request(db, request, action="reviewed_promise_submitted", user_id=admin.id,
                     resource="reviewed_civic_promise", details={"person_id": body.person_id})
    db.commit(); db.refresh(item)
    return {"id": item.id, "review_status": item.review_status,
            "message": "A different administrator must review this record."}


@router.post("/admin/reviewed-promises/{promise_id}/review")
def review_civic_promise(promise_id: int, body: ReviewedPromiseDecision, request: Request, response: Response,
                         admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    item = db.get(ReviewedCivicPromise, promise_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Reviewed promise record not found")
    if item.review_status != "pending":
        raise HTTPException(status_code=409, detail="Promise record has already been reviewed")
    if item.submitted_by_user_id == admin.id:
        raise HTTPException(status_code=403, detail="A different administrator must review this promise")
    item.review_status = body.decision; item.reviewed_by_user_id = admin.id
    item.reviewed_at = datetime.now(timezone.utc)
    log_from_request(db, request, action=f"reviewed_promise_{body.decision}", user_id=admin.id,
                     resource="reviewed_civic_promise", resource_id=str(item.id), details={"reason": body.reason})
    db.commit()
    return {"id": item.id, "review_status": item.review_status,
            "forecast_feature_enabled": promise_forecasts_enabled()}


@router.get("/reviewed-promises")
def list_approved_reviewed_promises(response: Response, limit: int = Query(default=50, ge=1, le=100),
                                    db: Session = Depends(get_db)):
    _protect_private_forecast_response(response)
    items = db.query(ReviewedCivicPromise).filter_by(review_status="approved").order_by(
        ReviewedCivicPromise.deadline.asc()).limit(limit).all()
    return {"forecast_feature_enabled": promise_forecasts_enabled(), "items": [{
        "id": p.id, "person_id": p.person_id, "person_name": p.person_name, "office": p.office,
        "exact_quote": p.exact_quote, "source_url": p.source_url,
        "promise_date": p.promise_date.isoformat(), "jurisdiction": p.jurisdiction,
        "government_level": p.government_level, "deadline": p.deadline.isoformat(),
        "measurable_criteria": p.measurable_criteria, "evidence_plan": p.evidence_plan,
        "template_version": p.template_version,
    } for p in items]}
