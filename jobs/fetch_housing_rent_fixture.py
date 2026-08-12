"""Build a reviewed Housing & Rent fixture from bounded official APIs.

Nothing in this module runs at application startup. Tests inject a fake
transport; the CLI requires explicit credentials and an output path.
"""

import argparse
import json
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence

import requests

from jobs.housing_rent_contract import CURATED_BILLS, ISSUE_SLUG, classify_phase
from utils.congress_urls import congress_bill_url


HUD_STATES = tuple(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split()
)
BLS_WAGE_SERIES_ID = "CES0500000003"
BLS_RENT_SERIES_ID = "CUSR0000SEHA"
HUD_SOURCE_URL = "https://www.huduser.gov/portal/dataset/fmr-api.html"
BLS_SOURCE_URL = "https://www.bls.gov/developers/"
BLS_RENT_SOURCE_URL = "https://www.bls.gov/cpi/factsheets/owners-equivalent-rent-and-rent.htm"


def _numeric(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class JsonTransport(Protocol):
    def get(self, url: str, *, params=None, headers=None) -> dict[str, Any]: ...
    def post(self, url: str, *, json=None) -> dict[str, Any]: ...


class RequestsTransport:
    def get(self, url: str, *, params=None, headers=None) -> dict[str, Any]:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def post(self, url: str, *, json=None) -> dict[str, Any]:
        response = requests.post(url, json=json, timeout=30)
        response.raise_for_status()
        return response.json()


def fetch_hud_fmr_proxy(
    transport: JsonTransport,
    api_key: str,
    years: Sequence[int],
    states: Sequence[str] = HUD_STATES,
) -> list[dict[str, Any]]:
    """Calculate the median of HUD area-level two-bedroom FMR values."""

    observations = []
    for year in years:
        values: list[float] = []
        for state in states:
            payload = transport.get(
                f"https://www.huduser.gov/hudapi/public/fmr/statedata/{state}",
                params={"year": year},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            for county in (payload.get("data") or {}).get("counties") or []:
                value = county.get("Two-Bedroom")
                if value is None and isinstance(county.get("fmr"), dict):
                    value = county["fmr"].get("2br")
                if value is not None:
                    values.append(float(value))
        if values:
            observations.append(
                {
                    "date": f"{year}-01-01",
                    "value": round(statistics.median(values), 2),
                    "source_record_id": f"HUD-FMR-2BR-AREA-MEDIAN-{year}",
                }
            )
    return observations


def fetch_bls_wages(
    transport: JsonTransport, years: Sequence[int], api_key: str | None = None
) -> list[dict[str, Any]]:
    body = {
        "seriesid": [BLS_WAGE_SERIES_ID],
        "startyear": str(min(years)),
        "endyear": str(max(years)),
    }
    if api_key:
        body["registrationkey"] = api_key
    payload = transport.post(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/", json=body
    )
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API error: {payload.get('message')}")
    points = payload["Results"]["series"][0]["data"]
    by_year: dict[int, list[float]] = {}
    for point in points:
        period = str(point.get("period", ""))
        if period not in {f"M{month:02d}" for month in range(1, 13)}:
            continue
        year = int(point["year"])
        value = _numeric(point.get("value"))
        if year in years and value is not None:
            by_year.setdefault(year, []).append(value)
    return [
        {
            "date": f"{year}-01-01",
            "value": round(statistics.mean(values), 2),
            "source_record_id": f"{BLS_WAGE_SERIES_ID}-{year}-ANNUAL-MEAN",
        }
        for year, values in sorted(by_year.items())
        if values
    ]


def fetch_bls_rent_index(
    transport: JsonTransport, years: Sequence[int], api_key: str | None = None
) -> list[dict[str, Any]]:
    """Return annual means for the U.S. city-average rent CPI index."""
    body = {
        "seriesid": [BLS_RENT_SERIES_ID],
        "startyear": str(min(years)),
        "endyear": str(max(years)),
    }
    if api_key:
        body["registrationkey"] = api_key
    payload = transport.post(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/", json=body
    )
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API error: {payload.get('message')}")
    points = payload["Results"]["series"][0]["data"]
    by_year: dict[int, list[float]] = {}
    for point in points:
        if str(point.get("period", "")) not in {
            f"M{month:02d}" for month in range(1, 13)
        }:
            continue
        year = int(point["year"])
        value = _numeric(point.get("value"))
        if year in years and value is not None:
            by_year.setdefault(year, []).append(value)
    return [
        {
            "date": f"{year}-01-01",
            "value": round(statistics.mean(values), 3),
            "source_record_id": f"{BLS_RENT_SERIES_ID}-{year}-ANNUAL-MEAN",
        }
        for year, values in sorted(by_year.items())
        if values
    ]


def _congress_get(transport, path: str, api_key: str) -> dict[str, Any]:
    return transport.get(
        f"https://api.congress.gov/v3{path}",
        params={"format": "json", "limit": 250, "api_key": api_key},
    )


def _status_bucket(detail: dict[str, Any], actions: list[dict[str, Any]]) -> str:
    text = "\n".join(str(action.get("text", "")) for action in actions).lower()
    if detail.get("laws") or "became public law" in text or "signed by president" in text:
        return "enacted"
    if "passed senate" in text or "passed/agreed to in senate" in text:
        return "passed_senate"
    if "passed house" in text or "passed/agreed to in house" in text:
        return "passed_house"
    if any(marker in text for marker in ("hearing", "markup", "ordered to be reported", "reported by")):
        return "in_committee"
    return "introduced"


def fetch_congress_bills(
    transport: JsonTransport, api_key: str
) -> list[dict[str, Any]]:
    output = []
    for spec in CURATED_BILLS:
        root = f"/bill/{spec.congress}/{spec.bill_type}/{spec.bill_number}"
        detail = _congress_get(transport, root, api_key)["bill"]
        actions = _congress_get(transport, f"{root}/actions", api_key).get("actions", [])
        cosponsors = _congress_get(transport, f"{root}/cosponsors", api_key).get("cosponsors", [])
        committees = _congress_get(transport, f"{root}/committees", api_key).get("committees", [])
        status = _status_bucket(detail, actions)
        source_url = congress_bill_url(spec.congress, spec.bill_type, spec.bill_number)
        latest = detail.get("latestAction") or {}
        people = [
            {"bioguide_id": sponsor["bioguideId"], "role": "sponsor"}
            for sponsor in detail.get("sponsors", [])
            if sponsor.get("bioguideId")
        ]
        people.extend(
            {"bioguide_id": person["bioguideId"], "role": "cosponsor"}
            for person in cosponsors
            if person.get("bioguideId")
        )
        referrals = []
        for committee in committees:
            thomas_id = committee.get("systemCode") or committee.get("thomasId")
            if not thomas_id:
                continue
            referral_action = next(
                (
                    action
                    for action in reversed(actions)
                    if "referred" in str(action.get("text", "")).lower()
                ),
                None,
            )
            if referral_action is None:
                continue
            referrals.append(
                {
                    "thomas_id": thomas_id,
                    "name": committee.get("name") or thomas_id,
                    "chamber": str(committee.get("chamber", "")).lower(),
                    "official_url": committee.get("url"),
                    "referred_at": referral_action["actionDate"],
                    "action_date": f"{referral_action['actionDate']}T00:00:00Z",
                    "action_text": referral_action["text"],
                    "action_code": referral_action.get("actionCode"),
                    "source_url": source_url,
                }
            )
        output.append(
            {
                "bill_id": spec.bill_id,
                "title": detail.get("title") or spec.bill_id,
                "policy_area": (detail.get("policyArea") or {}).get("name"),
                "status_bucket": status,
                "status_reason": latest.get("text"),
                "latest_action_text": latest.get("text"),
                "latest_action_date": (
                    f"{latest['actionDate']}T00:00:00Z" if latest.get("actionDate") else None
                ),
                "phase": classify_phase(status, [a.get("text", "") for a in actions]),
                "source_url": source_url,
                "people": people,
                "committee_referrals": referrals,
            }
        )
    return output


def build_fixture(
    transport: JsonTransport,
    congress_api_key: str,
    years: Sequence[int],
    *,
    bls_api_key: str | None = None,
    retrieved_at: datetime | None = None,
) -> dict[str, Any]:
    retrieved = (retrieved_at or datetime.now(timezone.utc)).isoformat()
    bills = fetch_congress_bills(transport, congress_api_key)
    sources = [
        {"url": BLS_RENT_SOURCE_URL, "publisher": "BLS", "retrieved_at": retrieved},
        {"url": BLS_SOURCE_URL, "publisher": "BLS", "retrieved_at": retrieved},
        *[
            {"url": bill["source_url"], "publisher": "Congress.gov", "retrieved_at": retrieved}
            for bill in bills
        ],
    ]
    return {
        "issue": {
            "slug": ISSUE_SLUG,
            "title": "Housing & Rent",
            "summary": "Official rent and wage evidence with curated federal legislation.",
        },
        "sources": sources,
        "evidence_series": [
            {
                "key": "rent_cpi",
                "title": "Rent of primary residence price index",
                "unit": "CPI index, Dec. 1982=100",
                "source_url": BLS_RENT_SOURCE_URL,
                "methodology_note": (
                    "Annual mean of monthly BLS CPI series CUSR0000SEHA; "
                    "this measures rent price change, not rent dollars."
                ),
                "observations": fetch_bls_rent_index(transport, years, bls_api_key),
            },
            {
                "key": "avg_wage",
                "title": "Average hourly earnings, total private",
                "unit": "USD per hour",
                "source_url": BLS_SOURCE_URL,
                "methodology_note": "Annual mean of monthly BLS CES0500000003 values; not median wages.",
                "observations": fetch_bls_wages(transport, years, bls_api_key),
            },
        ],
        "bills": bills,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=datetime.now().year)
    args = parser.parse_args()
    congress_key = os.getenv("CONGRESS_API_KEY") or os.getenv("API_KEY_CONGRESS")
    if not congress_key:
        parser.error("CONGRESS_API_KEY is required to generate a complete fixture")
    payload = build_fixture(
        RequestsTransport(),
        congress_key,
        range(args.start_year, args.end_year + 1),
        bls_api_key=os.getenv("BLS_API_KEY"),
    )
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
