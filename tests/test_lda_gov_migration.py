from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECT_LDA_JOBS = [
    "sync_finance_political_data.py",
    "sync_health_political_data.py",
    "sync_energy_data.py",
    "sync_transportation_data.py",
    "sync_defense_data.py",
    "sync_chemicals_data.py",
    "sync_agriculture_data.py",
    "sync_telecom_data.py",
    "sync_education_data.py",
]


def test_connector_uses_current_lda_gov_api_and_anonymous_rate_limit():
    connector = (ROOT / "connectors" / "senate_lda.py").read_text(encoding="utf-8")

    assert 'LDA_BASE = "https://lda.gov/api/v1/filings/"' in connector
    assert "lda.senate.gov/api" not in connector
    assert "POLITE_DELAY = 4.1" in connector
    assert 'os.getenv("LDA_SYNC_START_YEAR", "2020")' in connector


def test_direct_sector_jobs_share_lda_gov_throttle_and_year_window():
    for filename in DIRECT_LDA_JOBS:
        job = (ROOT / "jobs" / filename).read_text(encoding="utf-8")
        lobbying = job[job.index("def fetch_lobbying"):]

        assert "from connectors.senate_lda import LDA_BASE, POLITE_DELAY" in job
        assert "time.sleep(POLITE_DELAY)" in lobbying
        assert 'os.getenv("LDA_SYNC_START_YEAR", "2020")' in lobbying


def test_2026_influence_workflow_bounds_lda_sync_to_current_year():
    workflow = (
        ROOT / ".github" / "workflows" / "sync-politics-influence.yml"
    ).read_text(encoding="utf-8")

    assert "LDA_SYNC_START_YEAR=2026" in workflow
    assert "export DATABASE_URL LDA_SYNC_START_YEAR" in workflow
