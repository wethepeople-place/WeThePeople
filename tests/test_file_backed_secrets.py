from pathlib import Path

import pytest

from utils.secrets import get_secret


ROOT = Path(__file__).resolve().parents[1]


def test_file_secret_takes_precedence_and_strips_only_surrounding_space(monkeypatch, tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("  file-value\n", encoding="utf-8")
    monkeypatch.setenv("EXAMPLE_SECRET", "environment-value")
    monkeypatch.setenv("EXAMPLE_SECRET_FILE", str(secret))
    assert get_secret("EXAMPLE_SECRET") == "file-value"


def test_configured_secret_file_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAMPLE_SECRET", "stale-environment-value")
    monkeypatch.setenv("EXAMPLE_SECRET_FILE", str(tmp_path / "missing"))
    with pytest.raises(RuntimeError, match="could not be read"):
        get_secret("EXAMPLE_SECRET")


def test_required_and_empty_secret_contract(monkeypatch, tmp_path):
    monkeypatch.delenv("EXAMPLE_SECRET", raising=False)
    monkeypatch.delenv("EXAMPLE_SECRET_FILE", raising=False)
    with pytest.raises(RuntimeError, match="must be configured"):
        get_secret("EXAMPLE_SECRET", required=True)
    empty = tmp_path / "empty"
    empty.write_text("\n", encoding="utf-8")
    monkeypatch.setenv("EXAMPLE_SECRET_FILE", str(empty))
    with pytest.raises(RuntimeError, match="is empty"):
        get_secret("EXAMPLE_SECRET")


def test_sensitive_integrations_use_file_aware_loader():
    expected = {
        "services/jwt_auth.py": 'get_secret("WTP_JWT_SECRET", required=True)',
        "services/auth.py": 'get_secret("WTP_PRESS_API_KEY")',
        "services/press_signed_token.py": 'get_secret("WTP_PRESS_API_KEY")',
        "utils/http_client.py": 'get_secret("API_KEY_GOOGLE_CIVIC")',
        "connectors/usajobs.py": 'get_secret("USAJOBS_API_KEY")',
    }
    for relative, expression in expected.items():
        assert expression in (ROOT / relative).read_text(encoding="utf-8")
