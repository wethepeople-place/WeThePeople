from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_house_trade_sync_uses_canonical_database_and_fails_closed():
    source = (ROOT / "jobs" / "sync_trades_from_disclosures.py").read_text(
        encoding="utf-8"
    )

    assert "SessionLocal" in source
    assert "No active House members found in the canonical production database" in source


def test_full_politics_coverage_uses_real_member_bill_table():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-politics-2026.yml"
    ).read_text(encoding="utf-8")

    assert "member_bills_groundtruth" in workflow
    assert "member_bill_ground_truth" not in workflow


def test_targeted_house_trade_retry_checks_for_imported_rows():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-house-trades-2026.yml"
    ).read_text(encoding="utf-8")

    assert "sync_trades_from_disclosures.py --year 2026" in workflow
    assert 'assert row[0] > 0, "No House trades were imported"' in workflow
