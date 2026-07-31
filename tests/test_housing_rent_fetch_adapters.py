from datetime import datetime, timezone

from jobs.fetch_housing_rent_fixture import (
    BLS_WAGE_SERIES_ID,
    build_fixture,
    fetch_bls_wages,
    fetch_hud_fmr_proxy,
)
from jobs.housing_rent_contract import CURATED_BILLS
from jobs.load_housing_rent_slice import validate_fixture


class FakeTransport:
    def __init__(self):
        self.get_calls = []
        self.post_calls = []

    def get(self, url, *, params=None, headers=None):
        self.get_calls.append((url, params, headers))
        if "huduser.gov" in url:
            state = url.rsplit("/", 1)[-1]
            return {"data": {"counties": [{"Two-Bedroom": 1000 if state == "MI" else 2000}]}}
        path = url.split("/v3", 1)[1]
        for spec in CURATED_BILLS:
            root = f"/bill/{spec.congress}/{spec.bill_type}/{spec.bill_number}"
            if path.startswith(root):
                if path.startswith(f"{root}/actions"):
                    return {"actions": [{"actionDate": "2025-01-03", "text": "Referred to committee"}]}
                if path.startswith(f"{root}/cosponsors"):
                    return {"cosponsors": [{"bioguideId": "C000001"}]}
                if path.startswith(f"{root}/committees"):
                    return {"committees": [{"systemCode": "HSBA", "name": "House Committee", "chamber": "House"}]}
                return {
                    "bill": {
                        "title": f"Bill {spec.bill_id}",
                        "policyArea": {"name": "Housing"},
                        "sponsors": [{"bioguideId": "S000001"}],
                        "latestAction": {"actionDate": "2025-01-03", "text": "Referred to committee"},
                    }
                }
        raise AssertionError(f"Unexpected GET {url}")

    def post(self, url, *, json=None):
        self.post_calls.append((url, json))
        return {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [{"data": [
                    {"year": "2025", "period": "M01", "value": "30.00"},
                    {"year": "2025", "period": "M02", "value": "32.00"},
                    {"year": "2025", "period": "M13", "value": "99.00"},
                ]}]
            },
        }


def test_hud_adapter_calculates_labeled_area_median_proxy():
    transport = FakeTransport()
    observations = fetch_hud_fmr_proxy(transport, "secret", [2025], states=["MI", "CA"])
    assert observations == [{
        "date": "2025-01-01",
        "value": 1500.0,
        "source_record_id": "HUD-FMR-2BR-AREA-MEDIAN-2025",
    }]
    assert all(call[2] == {"Authorization": "Bearer secret"} for call in transport.get_calls)


def test_bls_adapter_averages_months_without_double_counting_m13():
    transport = FakeTransport()
    observations = fetch_bls_wages(transport, [2025])
    assert observations[0]["value"] == 31.0
    assert observations[0]["source_record_id"] == f"{BLS_WAGE_SERIES_ID}-2025-ANNUAL-MEAN"


def test_fixture_builder_is_bounded_and_loader_compatible():
    transport = FakeTransport()
    payload = build_fixture(
        transport,
        "hud-secret",
        "congress-secret",
        [2025],
        states=["MI", "CA"],
        retrieved_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )
    validate_fixture(payload)
    assert len(payload["bills"]) == 7
    assert len(payload["evidence_series"]) == 2
    assert {bill["bill_id"] for bill in payload["bills"]} == {
        spec.bill_id for spec in CURATED_BILLS
    }
    assert len([call for call in transport.get_calls if "api.congress.gov" in call[0]]) == 28
    assert all("api_key" in call[1] for call in transport.get_calls if "api.congress.gov" in call[0])
