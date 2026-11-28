from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_house_trade_sync_uses_production_database_and_fails_closed():
    source = (ROOT / "jobs" / "sync_trades_from_disclosures.py").read_text(
        encoding="utf-8"
    )

    assert 'os.getenv("WTP_DB_URL") or os.getenv("DATABASE_URL")' in source
    assert "No active House members found" in source


def test_full_politics_coverage_uses_real_member_bill_table():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-politics-2026.yml"
    ).read_text(encoding="utf-8")

    assert "member_bills_groundtruth" in workflow
    assert "member_bill_ground_truth" not in workflow
