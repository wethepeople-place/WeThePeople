"""Public election-calendar fallbacks with explicit source attribution.

Google Civic remains the preferred provider for address-level ballot data. This
module fills the less-sensitive state calendar view when Civic is unavailable
or does not yet publish a state's elections.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from utils.logging import get_logger


logger = get_logger(__name__)

EVERY_ELECTION_CALENDAR_URL = "https://api.everyelection.app/elections/calendar"
MISSOURI_CALENDAR_URL = "https://www.sos.mo.gov/elections/calendar/{year}cal"
USER_AGENT = "WeThePeople/1.0 (public civic calendar; https://wethepeople.place)"


def _division_id(state_code: str) -> str:
    return f"ocd-division/country:us/state:{state_code.lower()}"


def _source(name: str, url: str, kind: str) -> dict[str, str]:
    return {"name": name, "url": url, "kind": kind}


def list_every_election_calendar(
    state_code: str,
    start: date,
    end: date,
) -> Optional[list[dict[str, Any]]]:
    """Return a state's public Every Election API calendar, or None on failure."""
    try:
        response = requests.get(
            EVERY_ELECTION_CALENDAR_URL,
            params={"state": state_code.upper(), "from": start.isoformat(), "to": end.isoformat()},
            headers={"User-Agent": USER_AGENT},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Every Election calendar request failed (%s)", type(exc).__name__)
        return None

    items: list[dict[str, Any]] = []
    candidates = list(payload.get("elections") or []) + list(payload.get("upcoming") or [])
    for election in candidates:
        election_day = election.get("election_date")
        if not election_day:
            continue
        try:
            parsed_day = date.fromisoformat(election_day)
        except ValueError:
            continue
        if parsed_day < start or parsed_day > end:
            continue
        election_id = str(election.get("id") or hashlib.sha256(
            f"{state_code}|{election_day}|{election.get('name', '')}".encode()
        ).hexdigest()[:16])
        detail_url = f"https://everyelection.app/elections/{election_id}"
        items.append({
            "id": f"every-election:{election_id}",
            "name": election.get("name") or f"{state_code.upper()} election",
            "electionDay": election_day,
            "ocdDivisionId": _division_id(state_code),
            "description": election.get("election_type") or None,
            "registrationDeadline": election.get("registration_deadline") or None,
            "source": _source("Every Election API", detail_url, "public_api"),
        })
    return items


def _parse_missouri_calendar(html: str, year: int, today: date) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    source_url = MISSOURI_CALENDAR_URL.format(year=year)
    items: list[dict[str, Any]] = []
    for row in soup.select("table tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
        if len(cells) < 2:
            continue
        match = re.search(r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", cells[0])
        if not match:
            continue
        try:
            election_day = datetime.strptime(match.group(1), "%B %d, %Y").date()
        except ValueError:
            continue
        if election_day < today:
            continue
        style = cells[1]
        registration_deadline = None
        if len(cells) > 2:
            deadline_match = re.search(r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", cells[2])
            if deadline_match:
                try:
                    registration_deadline = datetime.strptime(
                        deadline_match.group(1), "%B %d, %Y"
                    ).date().isoformat()
                except ValueError:
                    pass
        digest = hashlib.sha256(f"MO|{election_day}|{style}".encode()).hexdigest()[:16]
        items.append({
            "id": f"mo-sos:{digest}",
            "name": style if len(style) <= 100 else f"Missouri election · {match.group(1)}",
            "electionDay": election_day.isoformat(),
            "ocdDivisionId": _division_id("MO"),
            "description": style,
            "registrationDeadline": registration_deadline,
            "source": _source("Missouri Secretary of State", source_url, "official_calendar"),
        })
    return items


def list_missouri_official_calendar(today: date) -> Optional[list[dict[str, Any]]]:
    """Read current and next-year dates from Missouri's official calendar."""
    items: list[dict[str, Any]] = []
    succeeded = False
    for year in (today.year, today.year + 1):
        try:
            response = requests.get(
                MISSOURI_CALENDAR_URL.format(year=year),
                headers={"User-Agent": USER_AGENT},
                timeout=12,
            )
            response.raise_for_status()
            succeeded = True
            items.extend(_parse_missouri_calendar(response.text, year, today))
        except requests.RequestException as exc:
            logger.warning("Missouri election calendar request failed for %s (%s)", year, type(exc).__name__)
    return items if succeeded else None


def list_state_calendar_fallbacks(
    state_code: str,
    today: Optional[date] = None,
) -> Optional[list[dict[str, Any]]]:
    """Merge keyless API data with an official state calendar when available."""
    current_day = today or date.today()
    end = current_day + timedelta(days=730)
    api_items = list_every_election_calendar(state_code, current_day, end)
    provider_succeeded = api_items is not None
    merged = list(api_items or [])

    if state_code.upper() == "MO":
        official_items = list_missouri_official_calendar(current_day)
        provider_succeeded = provider_succeeded or official_items is not None
        merged.extend(official_items or [])

    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for item in sorted(merged, key=lambda value: (value.get("electionDay") or "", value.get("name") or "")):
        key = (str(item.get("electionDay") or ""), str(item.get("name") or "").casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result if provider_succeeded else None
