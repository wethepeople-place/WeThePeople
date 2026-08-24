from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_forecast_controls_are_present_on_bills_and_elections():
    bill = (ROOT / "frontend/src/pages/BillDetailPage.tsx").read_text(encoding="utf-8")
    elections = (ROOT / "frontend/src/pages/ElectionsPage.tsx").read_text(encoding="utf-8")
    component = (ROOT / "frontend/src/components/ForecastCard.tsx").read_text(encoding="utf-8")
    assert "<ForecastCard billId={bill.bill_id}" in bill
    assert "contestToken={contest.forecast_token}" in elections
    assert "Community forecast" in component
    assert "No money, purchases, prizes, payouts, transferable credits, or financial contracts." in component
    assert "not polls, endorsements, official results, or voting advice" in component
    assert "Bet now" not in component


def test_forecast_schema_has_no_financial_balance_or_stake_fields():
    models = (ROOT / "models/forecast_models.py").read_text(encoding="utf-8")
    migration = (ROOT / "alembic_canonical/versions/20260823_civic_forecasting.py").read_text(encoding="utf-8")
    for forbidden in ("stake_amount", "payout", "wallet", "deposit", "withdrawal"):
        assert f'Column("{forbidden}"' not in models
        assert f'Column("{forbidden}"' not in migration


def test_forecast_legal_and_privacy_disclosures_are_published():
    terms = (ROOT / "frontend/src/pages/TermsOfUsePage.tsx").read_text(encoding="utf-8")
    privacy = (ROOT / "frontend/src/pages/PrivacyPolicyPage.tsx").read_text(encoding="utf-8")
    discovery = (ROOT / "frontend/src/pages/ForecastDiscoveryPage.tsx").read_text(encoding="utf-8")
    assert "not bets, wagers, polls, endorsements, official results, voting advice, or financial contracts" in terms
    assert "You must be at least 13" in terms
    assert "Your private Civic Forecast choice" in privacy
    assert "Account exports include your choices, and account anonymization deletes them" in privacy
    assert "Forecasts are not polls, endorsements, official results, or voting advice" in discovery
