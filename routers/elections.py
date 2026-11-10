"""Privacy-safe election information endpoints."""

import hashlib
import re
import threading
import time as monotonic_time
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator

from connectors.google_civic import CivicApiRateLimitError, CivicApiUnavailableError, list_elections_with_status, lookup_voter_info
from connectors.election_calendar import list_state_calendar_fallbacks
from services.forecast_tokens import sign_election_contest


router = APIRouter(prefix="/elections", tags=["elections"])

ELECTION_CATALOG_REFRESH_SECONDS = 15 * 60
ELECTION_CATALOG_RETRY_SECONDS = 60
_catalog_lock = threading.Lock()
_catalog_cache: dict[str, dict[str, Any]] = {}


def _reset_election_catalog_cache() -> None:
    """Clear process-local catalog state for deterministic tests."""
    with _catalog_lock:
        _catalog_cache.clear()


def _is_public_election(item: dict[str, Any]) -> bool:
    return bool(item.get("id")) and not re.search(r"\btest election\b", str(item.get("name") or ""), re.IGNORECASE)


def _catalog_payload(items: list[dict[str, Any]], fetched_at: datetime, status: str) -> dict[str, Any]:
    return {
        "items": [{
            "id": str(item.get("id") or ""),
            "name": item.get("name") or "Election",
            "election_day": item.get("electionDay") or None,
            "division_id": item.get("ocdDivisionId") or None,
            "description": item.get("description") or None,
            "registration_deadline": item.get("registrationDeadline") or None,
            "source": item.get("source") or {
                "name": "Google Civic Information API",
                "url": "https://developers.google.com/civic-information",
                "kind": "public_api",
            },
        } for item in items if _is_public_election(item)],
        "availability": {
            "status": status,
            "fetched_at": fetched_at.isoformat(),
            "refresh_after": (fetched_at + timedelta(seconds=ELECTION_CATALOG_REFRESH_SECONDS)).isoformat(),
        },
        "source": {"name": "Google Civic Information API + public official calendars", "official_only": False},
    }


class ElectionLookupRequest(BaseModel):
    address: str = Field(min_length=5, max_length=200)
    election_id: Optional[str] = Field(default=None, min_length=1, max_length=40)

    @field_validator("address", "election_id", mode="before")
    @classmethod
    def trim_input(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


def _source(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(item.get("name") or "Election authority"),
        "official": bool(item.get("official")),
    }


def _address(item: dict[str, Any]) -> dict[str, str]:
    allowed = ("locationName", "line1", "line2", "city", "state", "zip")
    return {key: str(item[key]) for key in allowed if item.get(key)}


def _location(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name") or (item.get("address") or {}).get("locationName"),
        "address": _address(item.get("address") or {}),
        "polling_hours": item.get("pollingHours") or None,
        "start_date": item.get("startDate") or None,
        "end_date": item.get("endDate") or None,
        "notes": item.get("notes") or None,
        "sources": [_source(source) for source in item.get("sources") or []],
    }


def _contest(item: dict[str, Any], election: dict[str, Any], source_url: str) -> dict[str, Any]:
    candidates = []
    forecast_options = []
    for candidate in item.get("candidates") or []:
        name = str(candidate.get("name") or "Candidate")
        party = candidate.get("party") or None
        key = hashlib.sha256(f"{name}|{party or ''}".casefold().encode()).hexdigest()[:20]
        candidates.append({
            "name": name,
            "party": party,
            "candidate_url": candidate.get("candidateUrl") or None,
            "forecast_key": key,
        })
        forecast_options.append({"key": key, "label": name, "party": party})
    result = {
        "type": item.get("type") or None,
        "office": item.get("office") or item.get("referendumTitle") or "Ballot question",
        "district": (item.get("district") or {}).get("name") or None,
        "candidates": candidates,
        "referendum_url": item.get("referendumUrl") or None,
        "sources": [_source(source) for source in item.get("sources") or []],
    }
    election_day = election.get("electionDay")
    if forecast_options and election.get("id") and election_day:
        closes_at = datetime.combine(datetime.fromisoformat(election_day).date(), time.min, tzinfo=timezone.utc)
        result["forecast_token"] = sign_election_contest({
            "election_id": str(election["id"]), "office": result["office"], "district": result["district"],
            "options": forecast_options, "closes_at": closes_at.isoformat(), "source_url": source_url,
        })
    else:
        result["forecast_token"] = None
    return result


def _authority(region: dict[str, Any]) -> dict[str, Any]:
    body = region.get("electionAdministrationBody") or {}
    return {
        "region": region.get("name") or "Election jurisdiction",
        "name": body.get("name") or "Election office",
        "election_info_url": body.get("electionInfoUrl") or None,
        "registration_url": body.get("electionRegistrationUrl") or None,
        "registration_status_url": body.get("electionRegistrationConfirmationUrl") or None,
        "voting_location_url": body.get("votingLocationFinderUrl") or None,
        "ballot_info_url": body.get("ballotInfoUrl") or None,
        "sources": [_source(source) for source in region.get("sources") or []],
    }


@router.get("")
def upcoming_elections(state: Optional[str] = Query(default=None, pattern=r"^[A-Za-z]{2}$")):
    state_code = state.upper() if state else None
    cache_key = state_code or "__all__"
    now_monotonic = monotonic_time.monotonic()
    with _catalog_lock:
        cached = _catalog_cache.get(cache_key)
        if cached and now_monotonic < cached["refresh_at"]:
            return _catalog_payload(cached["items"], cached["fetched_at"], cached["status"])
        try:
            items = list_elections_with_status()
        except (CivicApiRateLimitError, CivicApiUnavailableError):
            items = None

        if items is not None and state_code:
            state_marker = f"/state:{state_code.lower()}"
            items = [item for item in items if state_marker in str(item.get("ocdDivisionId") or "").lower() or item.get("ocdDivisionId") == "ocd-division/country:us"]

        if state_code:
            fallback_items = list_state_calendar_fallbacks(state_code)
            if fallback_items is not None:
                existing = {(str(item.get("electionDay") or ""), str(item.get("name") or "").casefold()) for item in items or []}
                items = list(items or [])
                items.extend(item for item in fallback_items if (str(item.get("electionDay") or ""), str(item.get("name") or "").casefold()) not in existing)

        if items is None:
            if cached:
                cached.update(status="stale", refresh_at=now_monotonic + ELECTION_CATALOG_RETRY_SECONDS)
                return _catalog_payload(cached["items"], cached["fetched_at"], "stale")
            raise HTTPException(status_code=503, detail="Election provider is temporarily unavailable. Coverage could not be checked.")
        fetched_at = datetime.now(timezone.utc)
        _catalog_cache[cache_key] = {"items": items, "fetched_at": fetched_at, "status": "available", "refresh_at": now_monotonic + ELECTION_CATALOG_REFRESH_SECONDS}
        return _catalog_payload(items, fetched_at, "available")


@router.post("/lookup")
def voter_information(body: ElectionLookupRequest, request: Request, response: Response):
    # Deliberately do not log, persist, echo, or attach the address to tracing.
    response.headers["Cache-Control"] = "no-store"
    try:
        google_election_id = body.election_id if body.election_id and body.election_id.isdigit() else None
        data = lookup_voter_info(body.address, google_election_id, official_only=True)
    except (CivicApiRateLimitError, CivicApiUnavailableError) as exc:
        raise HTTPException(status_code=503, detail="Election source is temporarily unavailable. Please try again shortly.") from exc
    if not data:
        raise HTTPException(status_code=404, detail="Exact ballot and polling-place details are not available from the provider for this address right now.")

    authorities = []
    for state in data.get("state") or []:
        authorities.append(_authority(state))
        local = state.get("local_jurisdiction")
        if isinstance(local, dict):
            authorities.append(_authority(local))

    election = data.get("election") or {}
    official_result_source = next(
        (office.get("election_info_url") for office in authorities if office.get("election_info_url")),
        "https://www.usa.gov/election-results",
    )
    return {
        "election": {
            "id": str(election.get("id") or ""),
            "name": election.get("name") or "Election",
            "election_day": election.get("electionDay") or None,
        },
        "mail_only": bool(data.get("mailOnly")),
        "polling_locations": [_location(item) for item in data.get("pollingLocations") or []],
        "early_vote_sites": [_location(item) for item in data.get("earlyVoteSites") or []],
        "drop_off_locations": [_location(item) for item in data.get("dropOffLocations") or []],
        "contests": [_contest(item, election, official_result_source) for item in data.get("contests") or []],
        "election_authorities": authorities,
        "privacy": {
            "address_retained": False,
            "registration_status_collected": False,
            "ballot_choices_collected": False,
        },
        "source": {"name": "Google Civic Information API", "official_only": True},
    }
