"""Civic forecasts: opinions, not gambling or financial products."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.auth_models import User
from models.database import Bill, get_db
from models.forecast_models import ForecastMarket, ForecastPrediction
from services.audit import log_from_request
from services.forecast_tokens import verify_election_contest
from services.jwt_auth import get_current_user, get_optional_user
from services.rbac import require_role

router = APIRouter(prefix="/forecasts", tags=["forecasts"])
MIN_PUBLIC_RESPONSES = 5


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


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


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
        "rules": "One changeable forecast per signed-in user. No money, purchases, prizes, payouts, or transferable points.",
    }


def _save_prediction(market: ForecastMarket, choice: str, user: User, db: Session) -> None:
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


@router.get("/bills/{bill_id}")
def bill_forecast(bill_id: str, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    market = db.query(ForecastMarket).filter_by(market_type="bill", subject_id=bill_id).first()
    if market is None:
        raise HTTPException(status_code=404, detail="No forecast has been opened for this bill")
    return _market_payload(market, db, user)


@router.put("/bills/{bill_id}")
def predict_bill(bill_id: str, body: PredictionWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bill = db.get(Bill, bill_id)
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found")
    market = _bill_market(bill, db)
    _save_prediction(market, body.option_key, user, db)
    return _market_payload(market, db, user)


@router.put("/elections")
def predict_election(body: ElectionPredictionWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
def election_forecast(body: ElectionMarketLookup, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    _, subject_id = _election_market_identity(body.contest_token)
    market = db.query(ForecastMarket).filter_by(market_type="election", subject_id=subject_id).first()
    if market is None:
        raise HTTPException(status_code=404, detail="No forecast has been opened for this contest")
    return _market_payload(market, db, user)


@router.patch("/admin/{market_id}")
def resolve_market(market_id: int, body: ResolutionWrite, request: Request,
                   admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    market = db.get(ForecastMarket, market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Forecast not found")
    if market.status in {"resolved", "void"}:
        raise HTTPException(status_code=409, detail="A final forecast resolution cannot be replaced")
    options = {str(option["key"]) for option in market.options_json}
    if body.status == "resolved" and body.resolved_option not in options:
        raise HTTPException(status_code=422, detail="Resolution must match a published option")
    market.status = body.status
    market.resolved_option = body.resolved_option if body.status == "resolved" else None
    market.resolution_source_url = body.source_url
    market.resolution_reason = body.reason
    market.resolved_by_user_id = admin.id
    market.resolved_at = datetime.now(timezone.utc)
    log_from_request(db, request, action="forecast_resolved", user_id=admin.id,
                     resource="forecast_market", resource_id=str(market.id),
                     details={"status": body.status, "option": body.resolved_option, "source_url": body.source_url, "reason": body.reason})
    db.commit()
    db.refresh(market)
    return _market_payload(market, db, admin)
