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


def test_all_state_sync_uses_conservative_rate_limit_settings():
    assert openstates.POLITE_DELAY >= 4.0
    assert openstates.MAX_RETRIES >= 5
