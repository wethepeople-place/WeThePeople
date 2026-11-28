import pytest

from connectors import openstates


class _Response:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "results": [
                {
                    "identifier": "HB 1",
                    "legislative_session": "2026rs",
                    "title": "Example bill",
                    "subject": ["Government"],
                    "latest_action_description": "Introduced",
                    "latest_action_date": "2026-01-10",
                    "sponsorships": [
                        {"name": "Ada Example", "primary": True}
                    ],
                    "sources": [{"url": "https://example.gov/hb1"}],
                    "openstates_url": "https://openstates.org/al/bills/2026rs/HB1/",
                }
            ]
        }


def test_bill_search_clamps_page_size_and_reads_v3_action_fields(monkeypatch):
    captured = {}

    def fake_get(url, *, params, headers, timeout):
        captured.update(
            url=url,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        return _Response()

    monkeypatch.setattr(openstates.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(openstates.requests, "get", fake_get)

    bills = openstates.fetch_state_bills("AL", per_page=50)

    assert captured["params"]["per_page"] == 20
    assert captured["params"]["include"] == ["sponsorships", "sources"]
    assert bills == [
        {
            "bill_id": "al-2026rs-HB1",
            "state": "AL",
            "session": "2026rs",
            "identifier": "HB 1",
            "title": "Example bill",
            "subjects": ["Government"],
            "latest_action": "Introduced",
            "latest_action_date": "2026-01-10",
            "sponsor_name": "Ada Example",
            "source_url": "https://example.gov/hb1",
        }
    ]


class _RateLimitedResponse:
    status_code = 429


def test_bill_search_retries_after_full_backoff(monkeypatch):
    responses = [
        _RateLimitedResponse(),
        _RateLimitedResponse(),
        _RateLimitedResponse(),
        _Response(),
    ]
    sleeps = []

    def fake_get(url, *, params, headers, timeout):
        return responses.pop(0)

    monkeypatch.setattr(openstates.time, "sleep", sleeps.append)
    monkeypatch.setattr(openstates.requests, "get", fake_get)

    bills = openstates.fetch_state_bills("AL")

    assert bills
    assert responses == []
    assert [5, 10, 20] == [delay for delay in sleeps if delay != openstates.POLITE_DELAY]


def test_openstates_pages_fail_closed_after_retries(monkeypatch):
    calls = 0

    def fake_get(url, *, params, headers, timeout):
        nonlocal calls
        calls += 1
        raise openstates.requests.exceptions.Timeout("boom")

    monkeypatch.setattr(openstates.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(openstates.requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="failed for 'AL' after retries"):
        openstates.fetch_state_bills("AL")

    assert calls == openstates.MAX_RETRIES == 4
