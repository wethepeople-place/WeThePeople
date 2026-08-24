"""Delete identifiable Civic Forecast choices after the approved retention period.

Fail-safe rules: finalized market, immutable receipt present, age >= configured
days, and dry-run unless ``--apply`` is explicitly supplied.
"""
import argparse
from datetime import datetime, timedelta, timezone

from models.database import SessionLocal
from models.forecast_models import ForecastMarket, ForecastPrediction, ForecastResolutionReceipt


def expire_forecast_predictions(db, *, retention_days: int = 365, apply: bool = False) -> dict:
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    eligible_ids = [row[0] for row in (
        db.query(ForecastMarket.id)
        .join(ForecastResolutionReceipt, ForecastResolutionReceipt.market_id == ForecastMarket.id)
        .filter(ForecastMarket.status.in_(("resolved", "void")), ForecastMarket.resolved_at <= cutoff)
        .distinct().all()
    )]
    count = db.query(ForecastPrediction).filter(ForecastPrediction.market_id.in_(eligible_ids)).count() if eligible_ids else 0
    if apply and eligible_ids:
        db.query(ForecastPrediction).filter(ForecastPrediction.market_id.in_(eligible_ids)).delete(synchronize_session=False)
        db.commit()
    return {"mode": "apply" if apply else "dry_run", "cutoff": cutoff.isoformat(),
            "eligible_markets": len(eligible_ids), "identifiable_choices": count,
            "deleted": count if apply else 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retention-days", type=int, default=365)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        print(expire_forecast_predictions(db, retention_days=args.retention_days, apply=args.apply))


if __name__ == "__main__":
    main()
