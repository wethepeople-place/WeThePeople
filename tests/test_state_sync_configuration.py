from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_state_sync_uses_canonical_database():
    source = (ROOT / "jobs" / "sync_state_data.py").read_text(encoding="utf-8")

    assert "from models.database import Base, SessionLocal, engine" in source
    assert "session = SessionLocal()" in source
    assert "create_engine(DB_PATH" not in source


def test_openstates_errors_include_bounded_response_details():
    source = (ROOT / "connectors" / "openstates.py").read_text(encoding="utf-8")

    assert "def _request_error_detail" in source
    assert "body[:1000]" in source


def test_state_workflow_splits_phases_and_requires_coverage():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-state-legislatures.yml"
    ).read_text(encoding="utf-8")

    assert "--legislators-only" in workflow
    assert "--bills-only" in workflow
    assert 'assert report["states"] >= 50' in workflow
    assert 'assert report["bills"] > 0' in workflow


def test_state_bill_sync_pages_against_api_page_size():
    source = (ROOT / "jobs" / "sync_state_data.py").read_text(encoding="utf-8")

    assert "page_size = 20" in source
    assert "per_page=page_size" in source
    assert "if len(bills) < page_size:" in source


def test_influence_workflow_seeds_entities_and_checks_coverage():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-politics-influence.yml"
    ).read_text(encoding="utf-8")

    assert "run_job jobs.seed_tracked_companies" in workflow
    assert "run_job jobs.seed_telecom_companies" in workflow
    assert "run_job jobs.seed_education_companies" in workflow
    assert "run_job jobs.sync_donations --cycle 2026" in workflow
    assert "assert lobbying > 0" not in workflow
    assert workflow.count("--skip-lobbying") >= 10
    assert "LDA.gov denied the production recovery host" in workflow
    assert "LDA_SYNC_START_YEAR=2026" in workflow
    assert "run_job jobs.sync_tech_data --skip-sec --skip-patents --skip-stocks --skip-contracts --skip-lobbying" in workflow
    assert "run_job jobs.sync_chemicals_data --skip-sec --skip-lobbying" in workflow
    assert "jobs.sync_chemicals_data --skip-sec --skip-emissions" not in workflow
    assert "assert contracts > 0" in workflow
    assert "assert enforcement > 0" in workflow
    assert "assert donations > 0" in workflow


def test_donation_sync_uses_canonical_production_database():
    source = (ROOT / "jobs" / "sync_donations.py").read_text(encoding="utf-8")

    assert "SessionLocal" in source
    assert "session = SessionLocal()" in source
    assert "create_engine" not in source
    assert 'os.getenv("DATABASE_URL"' not in source


def test_influence_workflow_binds_legacy_jobs_to_canonical_database():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-politics-influence.yml"
    ).read_text(encoding="utf-8")

    assert 'DATABASE_URL="${WTP_DB_URL:?WTP_DB_URL is required}"' in workflow
    assert "export DATABASE_URL" in workflow
    assert 'docker exec "$api_container" python -m jobs.' not in workflow
    assert workflow.count("run_job jobs.") >= 20
