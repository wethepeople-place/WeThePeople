"""Validate that Phase 4C candidate research remains a fail-closed shortlist."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CLEARANCE = frozenset({
    "agency_confirmation_of_federal_employee_authorship_or_explicit_license",
    "confirmation_of_no_restricted_third_party_video_audio_music_images_or_marks",
    "authorized_media_asset_or_delivery_method", "descriptive_poster_with_reuse_authority",
    "verified_duration_dimensions_and_aspect_ratio", "caption_track_or_caption_conformance_review",
    "transcript_review", "allowed_uses_and_attribution_language", "rights_reviewer_identity_and_timestamp",
    "accessibility_reviewer_identity_and_timestamp",
})


@dataclass(frozen=True)
class CandidateResearchValidation:
    valid: bool
    error_codes: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self) | {"error_codes": list(self.error_codes)}


def validate_candidate_research(*, root: Path = ROOT) -> CandidateResearchValidation:
    errors: set[str] = set()
    try:
        contract = json.loads((root / "config" / "watch_phase4c_candidate_research.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return CandidateResearchValidation(False, ("research_unreadable",))
    if contract.get("posture") != "research_only_no_download_no_publication" or contract.get("acceptance_catalog_unblocked") is not False:
        errors.add("research_boundary_drift")
    candidates = contract.get("shortlist", ())
    if not isinstance(candidates, list) or len(candidates) != 4 or len({item.get("candidate_id") for item in candidates if isinstance(item, dict)}) != 4:
        errors.add("shortlist_drift")
    for item in candidates if isinstance(candidates, list) else ():
        urls = [item.get("official_page_url", ""), item.get("transcript_url", ""), *item.get("official_evidence_urls", ())]
        if item.get("publisher") != "U.S. Census Bureau" or item.get("issue_fit") != "housing-rent":
            errors.add("candidate_scope_drift")
        if any(urlparse(url).scheme != "https" or not urlparse(url).netloc.endswith("census.gov") for url in urls):
            errors.add("candidate_provenance_drift")
        if item.get("rights_status") != "requires_item_level_agency_confirmation" or item.get("catalog_eligible") is not False:
            errors.add("rights_overclaim")
        if item.get("accessibility_status") != "official_transcript_present_captions_unverified":
            errors.add("accessibility_overclaim")
        if item.get("media_asset_status") != "embedded_third_party_player_no_reusable_asset_authorized" or item.get("poster_status") != "not_documented_for_reuse" or item.get("duration_status") != "not_verified":
            errors.add("asset_overclaim")
    if set(contract.get("required_clearance_packet_per_candidate", ())) != REQUIRED_CLEARANCE:
        errors.add("clearance_packet_drift")
    if contract.get("next_recommendation") != "request_item_level_clearance_and_asset_metadata_from_the_us_census_bureau":
        errors.add("recommendation_drift")
    try:
        doc = (root / "docs" / "phase4c" / "CANDIDATE_MEDIA_RESEARCH.md").read_text(encoding="utf-8").lower()
    except OSError:
        doc = ""
    if not all(anchor in doc for anchor in ("none is acceptance-ready or rights-cleared", "no video, poster, caption file, or transcript was downloaded", "catalog remains blocked", "requires separate authority")):
        errors.add("document_drift")
    return CandidateResearchValidation(not errors, tuple(sorted(errors)))
