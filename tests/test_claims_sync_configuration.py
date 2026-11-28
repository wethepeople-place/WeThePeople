from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_claims_workflow_backfills_evaluates_and_verifies_coverage():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-politics-claims-2026.yml"
    ).read_text(encoding="utf-8")

    assert "run_job jobs.backfill_claims_from_actions" in workflow
    assert "run_job jobs.evaluate_legislative_claims" in workflow
    assert 'assert report["claims"] > 0' in workflow
    assert 'assert report["evaluations"] > 0' in workflow
    assert 'd["total_claims"] > 0' in workflow
    assert 'd["total_evaluated"] > 0' in workflow
    assert 'DATABASE_URL="${WTP_DB_URL:?WTP_DB_URL is required}"' in workflow
