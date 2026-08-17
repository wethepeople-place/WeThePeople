import logging

import requests

from connectors import google_civic


def test_request_failure_does_not_log_address_or_api_key(monkeypatch, caplog):
    private_address = "123 Private Home Road"
    private_key = "secret-civic-key"
    monkeypatch.setattr(google_civic.config, "GOOGLE_CIVIC_API_KEY", private_key)

    def fail_request(*_args, **_kwargs):
        raise requests.RequestException(
            f"failed for https://example.test/voterinfo?address={private_address}&key={private_key}"
        )

    monkeypatch.setattr(requests, "get", fail_request)
    with caplog.at_level(logging.ERROR):
        assert google_civic.lookup_voter_info(private_address) is None

    assert private_address not in caplog.text
    assert private_key not in caplog.text
    assert "RequestException" in caplog.text
