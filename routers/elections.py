"""Privacy-safe, read-only election information endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from connectors.google_civic import CivicApiRateLimitError, list_elections, lookup_voter_info


router = APIRouter(prefix="/elections", tags=["elections"])


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


def _contest(item: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for candidate in item.get("candidates") or []:
        candidates.append({
            "name": candidate.get("name"),
            "party": candidate.get("party") or None,
            "candidate_url": candidate.get("candidateUrl") or None,
        })
    return {
        "type": item.get("type") or None,
        "office": item.get("office") or item.get("referendumTitle") or "Ballot question",
        "district": (item.get("district") or {}).get("name") or None,
        "candidates": candidates,
        "referendum_url": item.get("referendumUrl") or None,
        "sources": [_source(source) for source in item.get("sources") or []],
    }


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
def upcoming_elections():
    try:
        items = list_elections()
    except CivicApiRateLimitError as exc:
        raise HTTPException(status_code=503, detail="Election source is temporarily busy.") from exc
    return {
        "items": [{
            "id": str(item.get("id") or ""),
            "name": item.get("name") or "Election",
            "election_day": item.get("electionDay") or None,
            "division_id": item.get("ocdDivisionId") or None,
        } for item in items if item.get("id")],
        "source": {"name": "Google Civic Information API", "official_only": True},
    }


@router.post("/lookup")
def voter_information(body: ElectionLookupRequest, request: Request):
    # Deliberately do not log, persist, echo, or attach the address to tracing.
    try:
        data = lookup_voter_info(body.address, body.election_id, official_only=True)
    except CivicApiRateLimitError as exc:
        raise HTTPException(status_code=503, detail="Election source is temporarily busy.") from exc
    if not data:
        raise HTTPException(status_code=404, detail="No supported election information was found for that address.")

    authorities = []
    for state in data.get("state") or []:
        authorities.append(_authority(state))
        local = state.get("local_jurisdiction")
        if isinstance(local, dict):
            authorities.append(_authority(local))

    election = data.get("election") or {}
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
        "contests": [_contest(item) for item in data.get("contests") or []],
        "election_authorities": authorities,
        "privacy": {
            "address_retained": False,
            "registration_status_collected": False,
            "ballot_choices_collected": False,
        },
        "source": {"name": "Google Civic Information API", "official_only": True},
    }
