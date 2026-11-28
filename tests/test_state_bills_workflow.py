from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_targeted_state_bill_retry_skips_legislator_refetch():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-state-bills-2026.yml"
    ).read_text(encoding="utf-8")

    assert "--bills-only --max-pages 3 --stagger-sec 10" in workflow
    assert "--legislators-only" not in workflow
    assert 'assert report["states"] >= 45' in workflow
    assert 'assert report["bills"] >= 1000' in workflow
