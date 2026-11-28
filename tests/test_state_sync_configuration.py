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
