"""Automatically import and quality-check public Polymarket political markets."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.forecast_models import ExternalForecastAudit, ExternalForecastMarket, ForecastMarket

API_URL = "https://gamma-api.polymarket.com/events"
USER_AGENT = "WeThePeople-ForecastBot/1.0 (+https://wethepeople.place)"
MIN_VOLUME = 1_000.0
MIN_LIQUIDITY = 500.0
PUBLISH_SCORE = 85


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    try:
        result = json.loads(value or "[]")
        return result if isinstance(result, list) else []
    except (TypeError, ValueError):
        return []


def _date(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def assess(market: dict[str, Any], now: datetime) -> tuple[int, list[str], list[str], list[float], datetime | None]:
    reasons: list[str] = []
    score = 100
    question = str(market.get("question") or "").strip()
    description = str(market.get("description") or "").strip()
    outcomes = [str(v).strip() for v in _json_list(market.get("outcomes"))]
    try:
        prices = [float(v) for v in _json_list(market.get("outcomePrices"))]
    except (TypeError, ValueError):
        prices = []
    closes_at = _date(market.get("endDate"))
    volume = float(market.get("volumeNum") or market.get("volume") or 0)
    liquidity = float(market.get("liquidityNum") or market.get("liquidity") or 0)
    checks = [
        (bool(question) and question.endswith("?"), 15, "unclear_question"),
        (len(description) >= 80 and "resolve" in description.lower(), 20, "missing_resolution_rules"),
        (closes_at is not None and closes_at > now, 20, "invalid_or_past_close"),
        (bool(market.get("active")) and not bool(market.get("closed")) and bool(market.get("acceptingOrders", True)), 20, "not_actively_traded"),
        (len(outcomes) >= 2 and len(outcomes) == len(prices), 15, "invalid_outcomes"),
        (bool(prices) and all(0 <= p <= 1 for p in prices) and abs(sum(prices) - 1) <= .08, 10, "incoherent_prices"),
        (volume >= MIN_VOLUME, 10, "low_volume"),
        (liquidity >= MIN_LIQUIDITY, 10, "low_liquidity"),
    ]
    for passed, penalty, reason in checks:
        if not passed:
            score -= penalty
            reasons.append(reason)
    return max(score, 0), reasons, outcomes, prices, closes_at


def _match_local_market(db: Session, question: str, closes_at: datetime) -> int | None:
    """Only attach deterministic exact bill/election matches; fuzzy items stay external."""
    normalized = re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()
    bill = re.search(r"\b(h\s*r|s|h\s*j\s*res|s\s*j\s*res)\s*(\d+)\b", normalized)
    candidates = db.query(ForecastMarket).filter_by(status="open").all()
    if bill:
        digits = bill.group(2)
        matches = [m for m in candidates if m.market_type == "bill" and re.search(rf"(?:^|\D){digits}(?:\D|$)", m.subject_id)]
        return matches[0].id if len(matches) == 1 else None
    exact = [m for m in candidates if re.sub(r"[^a-z0-9]+", " ", m.question.lower()).strip() == normalized
             and abs((m.closes_at.replace(tzinfo=timezone.utc) - closes_at).total_seconds()) <= 86400]
    return exact[0].id if len(exact) == 1 else None


def fetch_events(session=requests) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for offset in range(0, 500, 100):
        response = session.get(API_URL, params={"active": "true", "closed": "false", "tag_slug": "politics", "limit": 100, "offset": offset},
                               headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        page = response.json()
        if not isinstance(page, list):
            raise ValueError("Polymarket returned a non-list events payload")
        events.extend(page)
        if len(page) < 100:
            break
    return events


def run(db: Session, *, transport=requests, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    counts = {"observed": 0, "published": 0, "quarantined": 0, "closed": 0}
    seen: set[str] = set()
    for event in fetch_events(transport):
        for market in event.get("markets") or []:
            market_id = str(market.get("id") or "")
            if not market_id:
                continue
            seen.add(market_id)
            score, reasons, outcomes, prices, closes_at = assess(market, now)
            if closes_at is None:
                continue
            status = "published" if score >= PUBLISH_SCORE else "quarantined"
            row = db.query(ExternalForecastMarket).filter_by(provider="polymarket", provider_market_id=market_id).first()
            old_status = row.quality_status if row else None
            old_prices = list(row.implied_probabilities_json or []) if row else []
            if row is None:
                row = ExternalForecastMarket(
                    provider="polymarket", provider_market_id=market_id,
                    question=str(market.get("question") or "").strip(), outcomes_json=outcomes,
                    implied_probabilities_json=prices, closes_at=closes_at,
                    source_url=f"https://polymarket.com/event/{event.get('slug')}?tid={market.get('slug')}",
                    quality_reasons_json=reasons, last_observed_at=now,
                )
                db.add(row); db.flush()
            row.provider_event_id = str(event.get("id") or "") or None
            row.slug = market.get("slug"); row.question = str(market.get("question") or "").strip()
            row.description = market.get("description"); row.outcomes_json = outcomes
            row.implied_probabilities_json = prices; row.volume = str(market.get("volumeNum") or market.get("volume") or 0)
            row.liquidity = str(market.get("liquidityNum") or market.get("liquidity") or 0)
            row.closes_at = closes_at; row.source_url = f"https://polymarket.com/event/{event.get('slug')}?tid={market.get('slug')}"
            row.category = "Politics"; row.quality_status = status; row.quality_score = score
            row.quality_reasons_json = reasons; row.last_observed_at = now
            row.matched_market_id = _match_local_market(db, row.question, closes_at)
            if status == "published" and row.published_at is None:
                row.published_at = now
            price_changed = len(old_prices) != len(prices) or any(abs(float(a) - float(b)) >= .01 for a, b in zip(old_prices, prices))
            action = "imported" if old_status is None else ("status_changed" if old_status != status else ("price_changed" if price_changed else None))
            if action:
                db.add(ExternalForecastAudit(external_market_id=row.id, action=action, score=score, reasons_json=reasons,
                                             observed_json={"prices": prices, "volume": row.volume, "liquidity": row.liquidity}))
            counts["observed"] += 1; counts[status] += 1
    stale_before = now - timedelta(hours=24)
    for row in db.query(ExternalForecastMarket).filter(ExternalForecastMarket.provider == "polymarket",
                                                       ExternalForecastMarket.last_observed_at < stale_before,
                                                       ExternalForecastMarket.quality_status == "published").all():
        row.quality_status = "quarantined"; row.quality_reasons_json = ["not_observed_for_24_hours"]
        db.add(ExternalForecastAudit(external_market_id=row.id, action="stale_quarantine", score=0,
                                     reasons_json=row.quality_reasons_json, observed_json={}))
        counts["quarantined"] += 1
    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Required safety acknowledgement")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing to write without --apply")
    db = SessionLocal()
    try:
        print(json.dumps(run(db), sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
