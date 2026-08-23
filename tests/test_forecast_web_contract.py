from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_forecast_controls_are_present_on_bills_and_elections():
    bill = (ROOT / "frontend/src/pages/BillDetailPage.tsx").read_text(encoding="utf-8")
    elections = (ROOT / "frontend/src/pages/ElectionsPage.tsx").read_text(encoding="utf-8")
    component = (ROOT / "frontend/src/components/ForecastCard.tsx").read_text(encoding="utf-8")
    assert "<ForecastCard billId={bill.bill_id}" in bill
    assert "contestToken={contest.forecast_token}" in elections
    assert "Community forecast" in component
    assert "No money, purchases, prizes, payouts, or transferable points." in component
    assert "Bet now" not in component


def test_forecast_schema_has_no_financial_balance_or_stake_fields():
    models = (ROOT / "models/forecast_models.py").read_text(encoding="utf-8")
    migration = (ROOT / "alembic_canonical/versions/20260823_civic_forecasting.py").read_text(encoding="utf-8")
    for forbidden in ("stake_amount", "payout", "wallet", "deposit", "withdrawal"):
        assert f'Column("{forbidden}"' not in models
        assert f'Column("{forbidden}"' not in migration
